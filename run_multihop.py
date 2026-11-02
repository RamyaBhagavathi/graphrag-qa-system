import os
import json
import time
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(override=True)

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY"),
    http_options=types.HttpOptions(timeout=90000)
)
MODEL = "gemini-3.1-flash-lite"
EMBED_MODEL = "gemini-embedding-001"
TOP_K = 5

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

chroma = chromadb.PersistentClient(path="chroma_db")
collection = chroma.get_collection("wiki_chunks")

RESULTS_FILE = "comparison_results_multihop.json"

QUESTIONS = [
    (1, "Which university awarded the CEO of Anthropic his PhD?", "Princeton University"),
    (2, "In what year was Daniela Amodei's brother born?", "1983"),
    (3, "Which company that Dario Amodei once worked at is also a cloud partner of Anthropic?", "Google"),
    (4, "Which US government department has partnered with both Anthropic and OpenAI?", "Department of Defense"),
    (5, "Which company expected to invest in Anthropic alongside Nvidia in November 2025 has also invested over $13 billion in OpenAI?", "Microsoft"),
    (6, "Who is the spouse of Anthropic's CEO?", "Camilla Clark"),
    (7, "What position did Anthropic's CEO hold at OpenAI before he left?", "Vice President of Research"),
]


def ask_gemini(prompt):
    for attempt in range(5):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  Gemini attempt {attempt + 1} failed. Retrying in 30 seconds...")
            time.sleep(30)
    return None


def clean_json(text):
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def get_all_entity_names():
    with driver.session(database=DATABASE) as session:
        result = session.run("MATCH (n:Entity) RETURN n.name AS name")
        return [record["name"] for record in result]


def find_entities_by_name(question, all_names):
    q = question.lower()
    return [n for n in all_names if len(n) > 2 and n.lower() in q]


def find_entities_by_gemini(question, all_names):
    prompt = (
        "Here is a list of entity names from a knowledge graph:\n"
        + json.dumps(all_names)
        + "\n\nQuestion: " + question
        + "\n\nReturn ONLY a JSON array (no other text) containing the names from the list "
        "that this question is about. Use the names exactly as written in the list. "
        "If none match, return []."
    )
    reply = ask_gemini(prompt)
    if reply is None:
        return []
    try:
        chosen = json.loads(clean_json(reply))
    except json.JSONDecodeError:
        return []
    return [name for name in chosen if name in all_names]


def find_entities(question, all_names):
    found = find_entities_by_name(question, all_names)
    for name in find_entities_by_gemini(question, all_names):
        if name not in found:
            found.append(name)
    return found


def get_facts(entity_name):
    direct_query = """
    MATCH (x:Entity {name: $name})-[r:RELATED_TO]-(y:Entity)
    RETURN DISTINCT startNode(r).name AS source, r.type AS rel, endNode(r).name AS target
    """
    indirect_query = """
    MATCH p = (x:Entity {name: $name})-[:RELATED_TO*2]-(y:Entity)
    UNWIND relationships(p) AS r
    WITH DISTINCT r
    RETURN startNode(r).name AS source, r.type AS rel, endNode(r).name AS target
    LIMIT 500
    """
    facts = []
    with driver.session(database=DATABASE) as session:
        for query in (direct_query, indirect_query):
            result = session.run(query, name=entity_name)
            for rec in result:
                fact = (rec["source"], rec["rel"], rec["target"])
                if fact not in facts:
                    facts.append(fact)
    return facts


def graph_pipeline(question, all_names):
    entities = find_entities(question, all_names)
    if not entities:
        return {"entities": [], "facts": 0, "answer": "NO ENTITIES MATCHED"}
    facts = []
    for name in entities:
        for fact in get_facts(name):
            if fact not in facts:
                facts.append(fact)
    fact_lines = "\n".join(f"{s} -- {rel} --> {t}" for s, rel, t in facts)
    prompt = (
        "Answer the question using ONLY the facts below. "
        "If the facts do not contain enough information, say so honestly.\n\n"
        "Facts:\n" + fact_lines + "\n\nQuestion: " + question
    )
    answer = ask_gemini(prompt)
    if answer is None:
        answer = "ERROR: Gemini busy"
    return {"entities": entities, "facts": len(facts), "answer": answer}


def embed_question(question):
    for attempt in range(5):
        try:
            result = client.models.embed_content(
                model=EMBED_MODEL,
                contents=[question],
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
            )
            return result.embeddings[0].values
        except Exception as e:
            print(f"  Embedding attempt {attempt + 1} failed. Retrying in 30 seconds...")
            time.sleep(30)
    return None


def vector_pipeline(question):
    vector = embed_question(question)
    if vector is None:
        return {"sources": [], "answer": "ERROR: embedding failed"}
    found = collection.query(query_embeddings=[vector], n_results=TOP_K)
    chunks = found["documents"][0]
    sources = [m["source"] for m in found["metadatas"][0]]
    context = "\n\n---\n\n".join(chunks)
    prompt = (
        "Answer the question using ONLY the text passages below. "
        "If the passages do not contain enough information, say so honestly.\n\n"
        "Passages:\n" + context + "\n\nQuestion: " + question
    )
    answer = ask_gemini(prompt)
    if answer is None:
        answer = "ERROR: Gemini busy"
    return {"sources": sources, "answer": answer}


results = {}
if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

all_names = get_all_entity_names()
print(f"Graph has {len(all_names)} entities. Vector store has {collection.count()} chunks.\n")

for number, question, key in QUESTIONS:
    old = results.get(str(number))
    if old and not old["graph"]["answer"].startswith("ERROR") and not old["vector"]["answer"].startswith("ERROR"):
        print(f"Q{number}: already done, skipping.")
        continue

    print(f"Q{number}: {question}")
    graph = graph_pipeline(question, all_names)
    time.sleep(3)
    vector = vector_pipeline(question)

    results[str(number)] = {
        "question": question,
        "answer_key": key,
        "graph": graph,
        "vector": vector,
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("  KEY:    ", key)
    print("  GRAPH:  ", graph["answer"][:350].replace("\n", " "))
    print("  VECTOR: ", vector["answer"][:350].replace("\n", " "))
    print()
    time.sleep(3)

driver.close()
print("Done. Full answers are saved in comparison_results.json")
