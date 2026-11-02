import os

DOCS_FOLDER = "documents"
MAX_CHARS = 20000

TERMS = [
    "Princeton",
    "1983",
    "1987",
    "worked at Google",
    "Department of Defense",
    "27%",
    "Satya Nadella",
    "$1 billion",
    "Camilla",
    "Microsoft",
]

texts = {}
for filename in sorted(os.listdir(DOCS_FOLDER)):
    if filename.endswith(".txt"):
        with open(os.path.join(DOCS_FOLDER, filename), "r", encoding="utf-8") as f:
            texts[filename] = f.read()

for term in TERMS:
    print("=" * 60)
    print("SEARCHING FOR:", term)
    for filename, text in texts.items():
        lower = text.lower()
        position = 0
        shown = 0
        while shown < 3:
            index = lower.find(term.lower(), position)
            if index == -1:
                break
            start = text.rfind(". ", 0, index) + 2
            end = text.find(". ", index)
            if end == -1:
                end = len(text)
            sentence = text[start:end + 1].replace("\n", " ").strip()
            where = "INSIDE" if index < MAX_CHARS else "OUTSIDE"
            print(f"  [{filename}] [{where}] {sentence[:300]}")
            shown += 1
            position = index + len(term)