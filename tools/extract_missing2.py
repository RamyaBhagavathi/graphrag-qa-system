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
SMALL = 2000

FILENAME = "anthropic_wikipedia.txt"
PIECES = [2, 4]

extraction_prompt = """Read the following piece of an article and extract ALL factual statements as triples.

Include every kind of fact:
- birth year, birthplace, nationality
- education
- jobs with dates
- founding, joining and leaving years
- roles and titles
- family relationships
- money amounts, acquisitions, lawsuits, partnerships, investments
- events and who was involved

Rules:
- Use the full, consistent name of each person or organization every time (for example always "Dario Amodei", never just "Dario" or "Amodei").
- Keep each value short (a name, a year, an amount, a place).
- Extract every distinct fact in this piece, up to 40.

Return ONLY a JSON array, with no extra text, where each item has this exact format:
{"entity1": "...", "relationship": "...", "entity2": "..."}

Text:
"""

with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    all_facts = json.load(f)
print(f"Starting with {len(all_facts)} facts already saved.")

with open(os.path.join(DOCS_FOLDER, FILENAME), "r", encoding="utf-8") as f:
    text = f.read()[:MAX_CHARS]
chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]

for number in PIECES:
    chunk = chunks[number - 1]
    halves = [chunk[:SMALL], chunk[SMALL:]]
    for half_number, part in enumerate(halves, start=1):
        label = f"piece {number}, half {half_number}"
        response = None
        for attempt in range(6):
            try:
                print(f"{label}, attempt {attempt + 1}...")
                response = client.models.generate_content(
                    model=MODEL,
                    contents=extraction_prompt + part
                )
                break
            except Exception as e:
                print("  Failed. Reason:", str(e)[:200])
                time.sleep(30)

        if response is None or not response.text:
            print(f"  No usable answer for {label}.")
            continue

        raw_output = response.text.strip()
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`")
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
            raw_output = raw_output.strip()

        try:
            facts = json.loads(raw_output)
        except json.JSONDecodeError:
            cut = raw_output.rfind("}")
            try:
                facts = json.loads(raw_output[:cut + 1] + "]")
                print("  (rescued a cut-off answer)")
            except json.JSONDecodeError:
                print(f"  Could not read the JSON for {label}.")
                continue

        all_facts.extend(facts)
        print(f"  Got {len(facts)} facts.")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_facts, f, indent=2)
        time.sleep(3)

print(f"\nDone! The file now has {len(all_facts)} facts.")