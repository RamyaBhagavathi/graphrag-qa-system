import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(override=True)
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

print("Connecting using:", uri.split("://")[0])

driver = GraphDatabase.driver(uri, auth=(user, password))
driver.verify_connectivity()
print("Connected to Neo4j successfully!")
driver.close()