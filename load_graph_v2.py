import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(override=True)

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

FILES = ["extracted_relationships.json", "extracted_relationships_v2.json", "extracted_relationships_v3.json"]

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

query = """
MERGE (a:Entity {name: $e1})
MERGE (b:Entity {name: $e2})
MERGE (a)-[r:RELATED_TO {type: $rel}]->(b)
"""

count = 0
skipped = 0

with driver.session(database=DATABASE) as session:
    for filename in FILES:
        with open(filename, "r", encoding="utf-8") as f:
            facts = json.load(f)
        print(f"Loading {len(facts)} facts from {filename}...")
        for fact in facts:
            try:
                e1 = str(fact["entity1"]).strip()
                rel = str(fact["relationship"]).strip()
                e2 = str(fact["entity2"]).strip()
            except (KeyError, TypeError):
                skipped += 1
                continue
            if not e1 or not rel or not e2:
                skipped += 1
                continue
            session.run(query, e1=e1, rel=rel, e2=e2)
            count += 1

    result = session.run("MATCH (n:Entity) RETURN count(n) AS nodes")
    nodes = result.single()["nodes"]
    result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS rels")
    rels = result.single()["rels"]

driver.close()
print(f"\nDone. Loaded {count} facts, skipped {skipped}.")
print(f"Graph now has {nodes} entities and {rels} relationships.")