import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY"),
    http_options=types.HttpOptions(timeout=90000)
)

DOCS_FOLDER = "documents"
OUTPUT_FILE = "extracted_relationships.json"
MAX_CHARS = 20000

extraction_prompt = """Read the following text carefully. Extract all factual relationships between named entities (people, organizations, companies, products) mentioned in it.

Return ONLY a JSON array, with no extra text, where each item has this exact format:
{"entity1": "...", "relationship": "...", "entity2": "..."}

Example:
[{"entity1": "Sam Altman", "relationship": "co-founded", "entity2": "OpenAI"}]

Text:
"""

all_relationships = []

for filename in os.listdir(DOCS_FOLDER):
    if filename.endswith(".txt"):
        filepath = os.path.join(DOCS_FOLDER, filename)
        print(f"Processing {filename}...")
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()[:MAX_CHARS]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"  Sending request (attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=extraction_prompt + text
                )
                break
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed ({e}). Retrying in 15 seconds...")
                time.sleep(15)
        else:
            print(f"  Skipping {filename} after {max_retries} failed attempts.")
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
            print(f"  Extracted {len(relationships)} relationships.")
        except json.JSONDecodeError:
            print(f"  Could not parse JSON from {filename}. Raw output:")
            print(raw_output[:500])

        time.sleep(2)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_relationships, f, indent=2)

print(f"\nDone! Saved {len(all_relationships)} total relationships to {OUTPUT_FILE}")