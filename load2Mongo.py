import json
import os

from pymongo import MongoClient

with open("graphifyoutput.json", encoding="utf-8") as f:
    graph = json.load(f)

# Update your connection string mongodb:// or mongodb+srv://
MONGODB_URI = "mongodb://<user>:<password>@localhost:27017/?retryWrites=true&w=majority&readPreference=secondaryPreferred"

client = MongoClient(MONGODB_URI)
# DB payment_graph
db = client["payments_graph"]

def update_fields(collection, document_id, fields, optional_fields=()):
    update = {"$set": fields}
    unset_fields = {field: "" for field in optional_fields if field not in fields}
    if unset_fields:
        update["$unset"] = unset_fields

    collection.update_one({"_id": document_id}, update, upsert=True)


# Upsert entities by stable Graphify ID, updating only mapped fields.
for node in graph["nodes"]:
    fields = {
        "kind": node.get("kind", "Entity"),
        "name": node.get("name", node["id"])
    }
    if "properties" in node:
        fields["properties"] = node["properties"]
    for field in ("traceId", "paymentId"):
        if node.get(field) is not None:
            fields[field] = node[field]

    update_fields(
        db.entities,
        node["id"],
        fields,
        optional_fields=("traceId", "paymentId")
    )

# Upsert directed relationships.
for edge in graph["edges"]:
    fields = {
        "from": edge["source"],
        "to": edge["target"],
        "type": edge.get("type", "RELATED_TO"),
        "graph": edge.get("graph", "architecture"),
        "active": edge.get("active", True)
    }
    if "properties" in edge:
        fields["properties"] = edge["properties"]
    if edge.get("traceId") is not None:
        fields["traceId"] = edge["traceId"]

    update_fields(
        db.relationships,
        f"edge:{edge['id']}",
        fields,
        optional_fields=("traceId")
    )


# Index the field followed at each traversal step; add reverse traversal support too.
db.relationships.create_index([("from", 1)])
db.relationships.create_index([("to", 1)])
db.relationships.create_index([("graph", 1), ("traceId", 1), ("from", 1)])
