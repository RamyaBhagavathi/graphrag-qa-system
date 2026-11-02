import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(override=True)
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

with open("extracted_relationships.json", "r", encoding="utf-8") as f:
    relationships = json.load(f)

query = """
MERGE (a:Entity {name: $e1})
MERGE (b:Entity {name: $e2})
MERGE (a)-[r:RELATED_TO {type: $rel}]->(b)
"""

with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
    count = 0
    for item in relationships:
        e1 = item.get("entity1")
        rel = item.get("relationship")
        e2 = item.get("entity2")
        if not (e1 and rel and e2):
            continue
        session.run(query, e1=str(e1).strip(), rel=str(rel).strip(), e2=str(e2).strip())
        count += 1

print(f"Loaded {count} relationships into Neo4j.")
driver.close()