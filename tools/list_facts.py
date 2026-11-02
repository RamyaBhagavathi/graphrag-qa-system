import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(override=True)

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

top_query = """
MATCH (n:Entity)-[r:RELATED_TO]-()
RETURN n.name AS name, count(r) AS degree
ORDER BY degree DESC
LIMIT 12
"""

fact_query = """
MATCH (x:Entity {name: $name})-[r:RELATED_TO]-(y:Entity)
RETURN DISTINCT startNode(r).name AS s, r.type AS rel, endNode(r).name AS t
LIMIT 40
"""

lines = []
with driver.session(database=DATABASE) as session:
    names = [rec["name"] for rec in session.run(top_query)]
    for name in names:
        lines.append(f"=== {name} ===")
        for rec in session.run(fact_query, name=name):
            lines.append(f"{rec['s']} -- {rec['rel']} --> {rec['t']}")
        lines.append("")

driver.close()

with open("facts_overview.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Saved {len(lines)} lines to facts_overview.txt")