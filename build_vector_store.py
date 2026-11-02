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
EMBED_MODEL = "gemini-embedding-001"

DOCS_FOLDER = "documents"
MAX_CHARS = 20000
CHUNK_SIZE = 1000
OVERLAP = 150
SKIP = ["sam_altman_wikipedia.txt"]


def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def embed_batch(texts):
    for attempt in range(5):
        try:
            result = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            print(f"  Embedding attempt {attempt + 1} failed ({e}). Retrying in 30 seconds...")
            time.sleep(30)
    return None


all_chunks = []
all_ids = []
all_meta = []

for filename in sorted(os.listdir(DOCS_FOLDER)):
    if not filename.endswith(".txt"):
        continue
    if filename.lower() in SKIP:
        print(f"Skipping {filename}")
        continue
    with open(os.path.join(DOCS_FOLDER, filename), "r", encoding="utf-8") as f:
        text = f.read()[:MAX_CHARS]
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        all_chunks.append(chunk)
        all_ids.append(f"{filename}-{i}")
        all_meta.append({"source": filename})
    print(f"{filename}: {len(chunks)} chunks")

print(f"\nTotal chunks: {len(all_chunks)}. Creating embeddings...")

all_vectors = []
BATCH = 20
for i in range(0, len(all_chunks), BATCH):
    batch = all_chunks[i:i + BATCH]
    vectors = embed_batch(batch)
    if vectors is None:
        print("Embedding failed after several attempts. Please run the script again in a few minutes.")
        raise SystemExit
    all_vectors.extend(vectors)
    print(f"  Embedded {len(all_vectors)} of {len(all_chunks)}")
    time.sleep(2)

chroma = chromadb.PersistentClient(path="chroma_db")
try:
    chroma.delete_collection("wiki_chunks")
except Exception:
    pass
collection = chroma.create_collection(name="wiki_chunks", metadata={"hnsw:space": "cosine"})
collection.add(
    ids=all_ids,
    documents=all_chunks,
    embeddings=all_vectors,
    metadatas=all_meta
)

print(f"\nDone! Stored {collection.count()} chunks in the 'chroma_db' folder.")