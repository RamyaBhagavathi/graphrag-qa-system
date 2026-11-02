import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(override=True)
print("NEO4J_DATABASE in .env:", os.getenv("NEO4J_DATABASE"))

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
with driver.session(database="system") as session:
    for record in session.run("SHOW DATABASES"):
        print(record["name"], "-", record["currentStatus"])
driver.close()