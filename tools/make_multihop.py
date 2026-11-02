src = open("run_comparison.py", "r", encoding="utf-8").read()

start = src.index("QUESTIONS = [")
end = src.index("\n]\n", start) + 3

new_list = '''QUESTIONS = [
    (1, "Which university awarded the CEO of Anthropic his PhD?", "Princeton University"),
    (2, "In what year was Daniela Amodei's brother born?", "1983"),
    (3, "Which company that Dario Amodei once worked at is also a cloud partner of Anthropic?", "Google"),
    (4, "Which US government department has partnered with both Anthropic and OpenAI?", "Department of Defense"),
    (5, "Which company expected to invest in Anthropic alongside Nvidia in November 2025 has also invested over $13 billion in OpenAI?", "Microsoft"),
    (6, "Who is the spouse of Anthropic's CEO?", "Camilla Clark"),
    (7, "What position did Anthropic's CEO hold at OpenAI before he left?", "Vice President of Research"),
]
'''

src = src[:start] + new_list + src[end:]
src = src.replace('RESULTS_FILE = "comparison_results.json"', 'RESULTS_FILE = "comparison_results_multihop.json"')

with open("run_multihop.py", "w", encoding="utf-8") as f:
    f.write(src)

print("Created run_multihop.py")