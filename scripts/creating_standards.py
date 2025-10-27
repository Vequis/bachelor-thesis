from pymongo import MongoClient
import os
from bson import ObjectId

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "official_db"

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

standards = db["standards"]

# definition_doc = {
#     "name": "extruder_profile",
#     "description": "Profile for extruder settings",
#     "fields": ["max_layer_z"],
#     "discard_others": True,
#     "optionals": ["printer_model"],
# }

# result = standards.insert_one(definition_doc)

# print("Inserted ID:", result.inserted_id)


def apply_standard(
    standard_id,
    source_coll_name: str,
    target_coll_name: str,
    *,
    drop_target_first: bool = False
):
    standards = db["standards"]
    source = db[source_coll_name]
    target = db[target_coll_name]

    if isinstance(standard_id, str):
        standard_id = ObjectId(standard_id)

    std = standards.find_one({"_id": standard_id})
    if not std:
        raise ValueError(f"Standard {standard_id} não encontrado.")

    required = set(std.get("fields", []))
    optionals = set(std.get("optionals", []))
    discard_others = bool(std.get("discard_others", False))

    print(required, optionals, discard_others)

    # clean target collection
    if drop_target_first:
        target.drop()

    to_insert = []


    for doc in source.find({}, {}):
        meta = doc.get("metadata", {}) or {}

        # Check required fields
        if not required.issubset(meta.keys()):
            continue

        if discard_others:
            # Keep only required + optional (present) from *metadata*
            selected = {k: meta[k] for k in required if k in meta}
            selected.update({k: meta[k] for k in optionals if k in meta})
            projected = selected
        else:
            # Keep the entire document (ensures full doc if it came with projection)
            projected = {k: v for k, v in doc.items() if k != "_id"}

        projected["standard_id"] = standard_id
        projected["source_id"] = doc["_id"]

        to_insert.append(projected)

    if to_insert:
        target.insert_many(to_insert)

    return {
        "standard_id": standard_id,
        "source_collection": source_coll_name,
        "target_collection": target_coll_name,
        "inserted_count": len(to_insert),
    }

if __name__ == "__main__":
    res = apply_standard(
        standard_id=ObjectId("68fad867a2429d9a2eff0215"),
        source_coll_name="print_sessions",
        target_coll_name="standardized_print_sessions",
        drop_target_first=True
    )
    print(res)