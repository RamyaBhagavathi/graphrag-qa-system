import os
import time
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY"),
    http_options=types.HttpOptions(timeout=90000)
)
MODEL = "gemini-3.1-flash-lite"
EMBED_MODEL = "gemini-embedding-001"
TOP_K = 5

chroma = chromadb.PersistentClient(path="chroma_db")
collection = chroma.get_collection("wiki_chunks")


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
            print(f"  Embedding attempt {attempt + 1} failed ({e}). Retrying in 30 seconds...")
            time.sleep(30)
    return None


def ask_gemini(prompt):
    for attempt in range(5):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  Gemini attempt {attempt + 1} failed ({e}). Retrying in 30 seconds...")
            time.sleep(30)
    return None


print(f"Connected. The vector store has {collection.count()} chunks.")

while True:
    question = input("\nAsk a question (or type 'quit'): ").strip()
    if question.lower() == "quit":
        break
    if not question:
        continue

    vector = embed_question(question)
    if vector is None:
        print("Could not process the question because Google was too busy. Please try again in a minute.")
        continue

    results = collection.query(query_embeddings=[vector], n_results=TOP_K)
    chunks = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    print("Retrieved chunks from:", sources)

    context = "\n\n---\n\n".join(chunks)
    prompt = (
        "Answer the question using ONLY the text passages below. "
        "If the passages do not contain enough information, say so honestly.\n\n"
        "Passages:\n" + context + "\n\nQuestion: " + question
    )
    answer = ask_gemini(prompt)
    if answer is None:
        print("\nGemini was too busy to answer. Please ask the question again in a minute.")
    else:
        print("\nAnswer:", answer)