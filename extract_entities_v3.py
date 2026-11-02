import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)
client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY"),
    http_options=types.HttpOptions(timeout=90000)
)
MODEL = "gemini-3.1-flash-lite"

DOCS_FOLDER = "documents"
OUTPUT_FILE = "extracted_relationships_v3.json"
MAX_CHARS = 20000
CHUNK_SIZE = 4000

extraction_prompt = """Read the following piece of an article and extract ALL factual statements as triples.

Include every kind of fact:
- birth year, birthplace, nationality (for example: Dario Amodei | born in year | 1983)
- education (for example: Dario Amodei | received PhD from | Princeton University)
- jobs with dates (for example: Dario Amodei | worked at | Baidu from November 2014 to October 2015)
- founding, joining and leaving years (for example: Dario Amodei | joined OpenAI in year | 2016)
- roles and titles (for example: Daniela Amodei | is president of | Anthropic)
- family relationships (for example: Dario Amodei | is sibling of | Daniela Amodei)
- money amounts, acquisitions, lawsuits, partnerships, investments
- events and who was involved

Rules:
- Use the full, consistent name of each person or organization every time (for example always "Dario Amodei", never just "Dario" or "Amodei").
- Keep each value short (a name, a year, an amount, a place).
- Extract every distinct fact in this piece, up to 60.

Return ONLY a JSON array, with no extra text, where each item has this exact format:
{"entity1": "...", "relationship": "...", "entity2": "..."}

Text:
"""

all_facts = []

for filename in sorted(os.listdir(DOCS_FOLDER)):
    if not filename.endswith(".txt"):
        continue
    filepath = os.path.join(DOCS_FOLDER, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()[:MAX_CHARS]

    chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    print(f"Processing {filename}: {len(chunks)} pieces")

    for number, chunk in enumerate(chunks, start=1):
        response = None
        for attempt in range(5):
            try:
                print(f"  Piece {number}/{len(chunks)}, attempt {attempt + 1}...")
                response = client.models.generate_content(
                    model=MODEL,
                    contents=extraction_prompt + chunk
                )
                break
            except Exception as e:
                print("  Failed. Retrying in 30 seconds...")
                time.sleep(30)

        if response is None:
            print(f"  Skipping piece {number} after 5 failed attempts.")
            continue

        raw_output = response.text.strip()
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`")
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
            raw_output = raw_output.strip()

        try:
            facts = json.loads(raw_output)
            all_facts.extend(facts)
            print(f"  Got {len(facts)} facts.")
        except json.JSONDecodeError:
            print("  Could not read the JSON for this piece. Skipping it.")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_facts, f, indent=2)
        time.sleep(3)

print(f"\nDone! Saved {len(all_facts)} total facts to {OUTPUT_FILE}")