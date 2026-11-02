import os

DOCS_FOLDER = "documents"

CHECKS = [
    ("Google", "anthropic_wikipedia.txt"),
    ("Nadella", "openai_wikipedia.txt"),
    ("Nadella", "sam_altman_wikipedia.txt"),
    ("2019", "openai_wikipedia.txt"),
]

lines = []
for term, filename in CHECKS:
    with open(os.path.join(DOCS_FOLDER, filename), "r", encoding="utf-8") as f:
        text = f.read()
    lower = text.lower()
    lines.append("=" * 60)
    lines.append(f"{term}  in  {filename}")
    position = 0
    shown = 0
    while shown < 8:
        index = lower.find(term.lower(), position)
        if index == -1:
            break
        start = max(0, index - 250)
        end = min(len(text), index + 350)
        where = "INSIDE" if index < 20000 else "OUTSIDE"
        snippet = text[start:end].replace("\n", " ")
        lines.append(f"[{where}] ...{snippet}...")
        lines.append("")
        shown += 1
        position = index + len(term)

with open("check2_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Saved check2_output.txt")