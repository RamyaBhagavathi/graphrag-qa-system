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
OUTPUT_FILE = "extracted_relationships_v2.json"
MAX_CHARS = 20000

extraction_prompt = """Read the following text carefully and extract ALL factual statements as triples.

Include every kind of fact, not only relationships between organizations and people:
- relationships between people and organizations (co-founded, CEO of, worked at, invested in, acquired, sibling of)
- years and dates (for example: Anthropic | founded in year | 2021)
- money amounts (for example: Anthropic | agreed to pay in settlement | $1.5 billion)
- roles and locations (for example: Jack Clark | leads | Anthropic Institute)
- education (for example: Dario Amodei | received PhD from | Princeton University)

Rules:
- Use the full, consistent name of each person or organization every time.
- Keep each value short (a name, a year, an amount, a place).
- Extract as many distinct facts as the text supports, up to 150.

Return ONLY a JSON array, with no extra text, where each item has this exact format:
{"entity1": "...", "relationship": "...", "entity2": "..."}

Text:
"""

all_relationships = []

for filename in sorted(os.listdir(DOCS_FOLDER)):
    if not filename.endswith(".txt"):
        continue
    filepath = os.path.join(DOCS_FOLDER, filename)
    print(f"Processing {filename}...")
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()[:MAX_CHARS]

    response = None
    for attempt in range(5):
        try:
            print(f"  Sending request (attempt {attempt + 1})...")
            response = client.models.generate_content(
                model=MODEL,
                contents=extraction_prompt + text
            )
            break
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed. Retrying in 30 seconds...")
            time.sleep(30)

    if response is None:
        print(f"  Skipping {filename} after 5 failed attempts. Run the script again later.")
        continue

    raw_output = response.text.strip()
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        relationships = json.loads(raw_output)
        all_relationships.extend(relationships)
        print(f"  Extracted {len(relationships)} facts.")
    except json.JSONDecodeError:
        print(f"  Could not read the JSON from {filename}. Raw output:")
        print(raw_output[:500])

    time.sleep(3)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_relationships, f, indent=2)

print(f"\nDone! Saved {len(all_relationships)} total facts to {OUTPUT_FILE}")