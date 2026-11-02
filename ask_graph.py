import os
import json
import time
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

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def ask_gemini(prompt):
    for attempt in range(5):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  Gemini attempt {attempt + 1} failed ({e}). Retrying in 30 seconds...")
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


def find_entities_in_question(question, all_names):
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
        print("  Could not read the entity list from Gemini:", reply[:200])
        return []
    return [name for name in chosen if name in all_names]


def get_facts(entity_name):
    query = """
    MATCH p = (x:Entity {name: $name})-[:RELATED_TO*1..2]-(y:Entity)
    UNWIND relationships(p) AS r
    WITH DISTINCT r
    RETURN startNode(r).name AS source, r.type AS rel, endNode(r).name AS target
    LIMIT 200
    """
    with driver.session(database=DATABASE) as session:
        result = session.run(query, name=entity_name)
        return [(rec["source"], rec["rel"], rec["target"]) for rec in result]


def answer_question(question, facts):
    fact_lines = "\n".join(f"{s} -- {rel} --> {t}" for s, rel, t in facts)
    prompt = (
        "Answer the question using ONLY the facts below. "
        "If the facts do not contain enough information, say so honestly.\n\n"
        "Facts:\n" + fact_lines + "\n\nQuestion: " + question
    )
    return ask_gemini(prompt)


all_names = get_all_entity_names()
print(f"Connected. The graph has {len(all_names)} entities.")

while True:
    question = input("\nAsk a question (or type 'quit'): ").strip()
    if question.lower() == "quit":
        break
    if not question:
        continue

    entities = find_entities_in_question(question, all_names)
    print("Entities found in your question:", entities)
    if not entities:
        print("I couldn't match your question to anything in the graph.")
        continue

    facts = []
    for name in entities:
        for fact in get_facts(name):
            if fact not in facts:
                facts.append(fact)
    print(f"Collected {len(facts)} connected facts from the graph.")

    answer = answer_question(question, facts)
    if answer is None:
        print("\nGemini was too busy to answer. Please ask the question again in a minute.")
    else:
        print("\nAnswer:", answer)

driver.close()