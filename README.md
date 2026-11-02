# GraphRAG Knowledge-Graph QA System

A question-answering system that turns Wikipedia articles into a **Neo4j knowledge graph** and answers questions by traversing it (GraphRAG). It is benchmarked against a plain **vector-RAG** baseline (ChromaDB) on a hand-verified question set.

Built with Python, Neo4j (Cypher), ChromaDB and the Google Gemini API, using free-tier tools only.

## Why this project

Standard vector RAG finds text passages that look similar to a question. It struggles when the answer needs several facts that sit in different passages or different articles. A knowledge graph stores facts as connected entities, so a question can follow links between them. This project tests whether that helps, with real numbers.

## How it works

1. **Extract:** an LLM reads each Wikipedia article in 4,000-character pieces and returns facts as `entity -- relationship --> entity`.
2. **Load:** the facts are written to Neo4j (`MERGE`, so duplicates are combined). The graph has 564 entities and 927 relationships.
3. **Answer (graph):** entities named in the question are found by name matching (with the LLM as a backup). Cypher collects their direct facts and facts two steps away. The LLM answers using only those facts.
4. **Answer (vector baseline):** the same articles are split into 63 chunks, embedded and stored in ChromaDB. The 5 closest chunks to the question go to the LLM.
5. **Compare:** both systems answer the same questions, and each answer is checked against an answer key verified by hand against the source text.

## Data

Four English Wikipedia articles: Anthropic, Dario Amodei, OpenAI and Sam Altman. Both systems read the same first 20,000 characters of each article, so the comparison is fair. The Sam Altman article is in the graph only. The article text is not included in this repository (Wikipedia content is licensed CC BY-SA); to rerun, save each article as plain text in a `documents/` folder.

## Results

**Test 1: 12 scored questions, mostly single-fact** (a 13th question was excluded as ambiguous because the article contradicts itself on the number of founders)

| System | Round 1 | Round 2 (after fixes) |
|---|---|---|
| GraphRAG | 3/12 | **11/12** |
| Vector RAG | 11/12 | **11/12** |

**Test 2: 7 multi-hop questions** (answers need facts from different passages or articles)

| System | Score |
|---|---|
| GraphRAG | **7/7** |
| Vector RAG | 5/7 (4/7 if one hedged answer is counted as wrong) |

**Where vector RAG failed:** it found the right text but did not connect it (for example, the PhD of Anthropic's CEO), and it did not retrieve the passage needed to link two articles (which company invested in Anthropic alongside Nvidia and has also put over $13 billion into OpenAI). The graph answered both.

## What went wrong first, and how it was fixed

The first graph scored 3/12. Diagnosing it found three causes, each fixed and re-measured:

- **Weak extraction prompt:** years, amounts and roles were never stored. A richer prompt and 4,000-character pieces raised the number of extracted facts (the graph grew from 125 to 564 entities).
- **Fragile entity matching:** asking the LLM to pick entity names from a list of hundreds sometimes returned nothing. Now names are matched in code first, with the LLM as a backup.
- **Retrieval cap:** a 150-fact limit on indirect facts cut off a key link. Raising it to 500 fixed one question.

## Limitations

- **Small test:** 19 scored questions in total. The results show a pattern, not proof.
- **Possible bias:** the multi-hop questions were drafted by reading the graph, which favours the graph. The fixes were also tuned on the first 12 questions.
- **Hallucinated facts:** the extraction model sometimes adds facts that are not in the text. For example, the graph contained a birth year that appears nowhere in the articles, and it labelled some investors as founders. A wrong fact in a graph looks as trustworthy as a correct one, so extraction needs verification (for example, requiring a quote from the text for each fact).
- **Messy relationship names:** the same fact is stored under several wordings, such as "CEO of" and "is CEO of".
- **Free-tier limits:** the Gemini API often returned 503 "high demand" errors, so the scripts use retries and save progress. Free Neo4j Aura instances pause after about 3 days of inactivity.

## Tech stack

Python 3.11, Neo4j AuraDB Free, Cypher, ChromaDB, Google Gemini API (`google-genai`), python-dotenv.

## Run it yourself

1. Create a virtual environment and install the packages: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your own keys (never commit `.env`).
3. Save the four articles as plain text in `documents/`.
4. Run in order:
```
   python extract_entities_v3.py
   python load_graph_v2.py
   python build_vector_store.py
   python run_comparison.py
   python run_multihop.py
```

## Main files

| File or folder | Purpose |
|---|---|
| `extract_entities_v3.py` | LLM extraction of facts in 4,000-character pieces |
| `load_graph_v2.py` | Loads extracted facts into Neo4j |
| `build_vector_store.py` | Builds the ChromaDB baseline |
| `ask_graph.py`, `ask_vector.py` | Interactive question answering for each system |
| `run_comparison.py` | Runs both systems on the first question set |
| `run_multihop.py` | Runs both systems on the multi-hop question set |
| `tools/` | Scripts that verify answer keys against the source text and inspect the graph |
| `results/` | Saved answers from every comparison run |
| `archive/` | Earlier versions of the extraction and loading scripts |