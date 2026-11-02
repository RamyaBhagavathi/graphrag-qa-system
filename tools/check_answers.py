import os

DOCS_FOLDER = "documents"
LIMIT = 20000

CHECKS = [
    (1, "anthropic_wikipedia.txt", "2021"),
    (2, "anthropic_wikipedia.txt", "acquired Bun"),
    (3, "anthropic_wikipedia.txt", "$1.5 billion"),
    (4, "anthropic_wikipedia.txt", "Anthropic Institute"),
    (5, "dario_amodei_wikipedia.txt", "1983"),
    (6, "dario_amodei_wikipedia.txt", "Princeton"),
    (7, "dario_amodei_wikipedia.txt", "Baidu"),
    (8, "dario_amodei_wikipedia.txt", "joined OpenAI"),
    (9, "anthropic_wikipedia.txt", "Vice President of Research"),
    (10, "anthropic_wikipedia.txt", "siblings"),
    (11, "anthropic_wikipedia.txt", "co-founder and CEO"),
    (12, "dario_amodei_wikipedia.txt", "replacing"),
    (13, "anthropic_wikipedia.txt", "seven"),
]

for number, filename, term in CHECKS:
    path = os.path.join(DOCS_FOLDER, filename)
    if not os.path.exists(path):
        print(f"Q{number}: file {filename} NOT FOUND")
        continue
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    pos = text.lower().find(term.lower())
    if pos == -1:
        print(f"Q{number}: '{term}' NOT FOUND in {filename}")
        print()
        continue
    if pos < LIMIT:
        where = "INSIDE the 20,000 limit"
    else:
        where = "OUTSIDE the 20,000 limit"
    start = max(0, pos - 120)
    end = min(len(text), pos + 160)
    snippet = text[start:end].replace("\n", " ")
    print(f"Q{number} [{filename}] '{term}' at character {pos} - {where}")
    print("    ..." + snippet + "...")
    print()