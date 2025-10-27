import io
import mimetypes
import os
from datetime import datetime
import uuid
import zipfile
from bson import ObjectId
from pymongo import MongoClient
import gridfs
import hashlib, json
import numpy as np
from scripts.classes.dataclass import DataClass
from scripts.imageprocessing import convert_to_png, extract_image_data

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "official_db"

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
fs = gridfs.GridFS(db)

def put_file(data: DataClass, metadata={}):
    existing = fs.find_one({"metadata.hash_id": data.hash_id})
    if existing:
        return existing._id

    return fs.put(
        data.bytes,
        filename=data.name,
        metadata={**metadata, "hash_id": data.hash_id}
    )

# Create functions:
# collection = db[]
# insert_one({...})
# ... 
# update_one({"_id": id}, {"$set": {...}})

def create_session(file_datas: list[DataClass], metadata={}, print_job_id=None, timeseries={}, image_collections_ids=[]):
    collection = db["print_sessions"]
    session_id = collection.insert_one({
        "inserted_at": datetime.now(),
        "status": "queued",
        "raw_files": {"file_ids": []},
        "metadata": metadata,
        "print_job_id": print_job_id,
        "timeseries": timeseries,
        "image_collections": image_collections_ids,
    }).inserted_id

    file_ids = [put_file(data, metadata={"session_id": session_id}) for data in file_datas]

    collection.update_one(
        {"_id": session_id},
        {"$set": {"status": "ingested", "raw_files.file_ids": file_ids}}
    )
    
    return session_id, file_ids

def get_all_sessions():
    collection = db["print_sessions"]
    sessions = list(collection.find({}))
    return sessions

def get_session_with_embedded_info(session_id):
    collection = db["print_sessions"]
    session = db["print_sessions"].find_one({"_id": ObjectId(session_id)})
    if session is None:
        return None

    # get print_job info
    pj_id = session.get("print_job_id")
    pj = db["print_jobs"].find_one({"_id": pj_id})
    if pj:
        session["print_job_info"] = pj

        ids_to_fetch = [pid for pid in [pj.get("printer_id"), pj.get("object_id")] if pid]
        if ids_to_fetch:
            docs = list(db["printers"].find({"_id": {"$in": ids_to_fetch}})) + \
                    list(db["objects"].find({"_id": {"$in": ids_to_fetch}}))
            for doc in docs:
                if doc["_id"] == pj.get("printer_id"):
                    session["printer_info"] = doc
                elif doc["_id"] == pj.get("object_id"):
                    session["object_info"] = doc

    # get image_collections info
    coll_ids = session.get("image_collections", [])
    collections = list(db["image_collections"].find({"_id": {"$in": coll_ids}}))
    img_ids = [img_id for coll in collections for img_id in coll.get("image_file_ids", [])]
    if img_ids:
        imgs = {img["_id"]: img for img in db["images"].find({"_id": {"$in": img_ids}})}
        for coll in collections:
            coll["images_info"] = [imgs[i] for i in coll.get("image_file_ids", []) if i in imgs]
    session["image_collections_info"] = collections

    # get timeseries info
    ts_map = session.get("timeseries", {})
    ts_ids = list(ts_map.values())
    ts_docs = {ts["_id"]: ts for ts in db["timeseries"].find({"_id": {"$in": ts_ids}})}
    session["timeseries_info"] = {
        name: ts_docs[ts_id] for name, ts_id in ts_map.items() if ts_id in ts_docs
    }

    return session

###### RAW FILES #######


def download_files_zip(file_ids: list):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for s in file_ids:
            oid = ObjectId(s)
            f = fs.get(oid)
            name = f.filename or str(oid)
            z.writestr(name, f.read())
    b.seek(0)
    return b.getvalue()

def download_file_as_dataclass(file_id):
    oid = ObjectId(file_id)
    f = fs.get(oid)

    return DataClass(data=f.read(), mime_type=mimetypes.guess_type(f.filename or str(oid))[0] or "application/octet-stream", name=f.filename or str(oid))


##### SCRIPTS #######

def create_script(file_data: DataClass):
    collection = db["scripts"]

    script_id = collection.insert_one({
        "status": "queued",
        "script_name": file_data.name.split(".")[0],
        "inserted_at": datetime.now(),
        "artifacts": {"file_id": []},
    }).inserted_id

    file_id = put_file(
        file_data,
        metadata={"script_id": script_id}
    )

    collection.update_one(
        {"_id": script_id},
        {"$set": {"status": "ingested", "artifacts.file_id": file_id}}
    )   
    return script_id, file_id

def get_file_id_from_script(script_id):
    collection = db["scripts"]
    script = collection.find_one({"_id": script_id})
    if script is None:
        return None
    return script.get("artifacts", {}).get("file_id", None)


####### OBJECTS #######

def handle_file_array(file_datas: list[DataClass]):
    for f in file_datas:
        if f is None:
            print("Removing None file")
            file_datas.remove(f)

    if (len(file_datas) == 0):
        file_datas = None
    return file_datas

def generate_hash(file_datas: list[DataClass]):
    if file_datas is None:
        return 0
    file_hashes = [hashlib.sha256(f.bytes).hexdigest() for f in file_datas]
    return hashlib.sha256(json.dumps(sorted(file_hashes)).encode()).hexdigest()


def create_object(file_datas: list[DataClass], extracted_data: dict):
    collection = db["objects"]
    handle_file_array(file_datas)
    hash_id = generate_hash(file_datas) # Generate a combined hash for all files

    existing = collection.find_one({"hash_id": hash_id})

    if file_datas is not None and existing is not None:
        return existing["_id"], existing.get("artifacts", {}).get("file_ids", [])
    else:    
        object_id = collection.insert_one({
            "status": "queued",
            "hash_id": hash_id,
            "inserted_at": datetime.now(),
            "artifacts": {"file_ids": []},
            "extracted_data": extracted_data
        }).inserted_id

        file_ids = [put_file(file_data, metadata={"object_id": object_id}) for file_data in file_datas]

        collection.update_one(
            {"_id": object_id},
            {"$set": {"status": "ingested", "artifacts.file_ids": file_ids}}
        )
        return object_id, file_ids

def create_printer(printer_id, printer_info={}):
    collection = db["printers"]

    exisiting = collection.find_one({"printer_id": printer_id})
    if exisiting is not None:
        return exisiting["_id"]
    else:
        printer_id = collection.insert_one({
            "printer_id": printer_id,
            "info": printer_info,
            "inserted_at": datetime.now(),
            "status": "active",
        }).inserted_id
        return printer_id

def check_print_job_exists(printer_id, object_id, file_datas: list[DataClass]):
    collection = db["print_jobs"]

    handle_file_array(file_datas)
    existing = collection.find_one({
        "printer_id": printer_id,
        "object_id": object_id,
        "artifacts.hash_id": generate_hash(file_datas)
    })
    return existing

def create_print_job(file_datas: list[DataClass], printer_id=None, object_id=None, metadata={}):
    collection = db["print_jobs"]

    existing = check_print_job_exists(printer_id, object_id, file_datas)

    if file_datas is not None and existing is not None:
        return existing["_id"], existing.get("artifacts", {}).get("file_ids", [])
    else:
        hash = generate_hash(file_datas)
        # combining this hash with generated hash from metadata
        metadata_hash = json.dumps(metadata, sort_keys=True)
        metadata_hash = hashlib.sha256(metadata_hash.encode()).hexdigest()
        combined_hash = hashlib.sha256()
        combined_hash.update(hash.encode())
        combined_hash.update(metadata_hash.encode())
        final_hash = combined_hash.hexdigest()

        job_id = collection.insert_one({
            "printer_id": printer_id,
            "object_id": object_id,
            "inserted_at": datetime.now(),
            "status": "queued",
            "artifacts": {"file_ids": [], "hash_id": final_hash},
            "metadata": metadata
        }).inserted_id

        file_ids = [put_file(data, metadata={"job_id": job_id}) for data in file_datas]

        collection.update_one(
            {"_id": job_id},
            {"$set": {"status": "ingested", "artifacts.file_ids": file_ids}}
        )
        
        return job_id, file_ids
    

##### TIMESERIES #####

def create_timeseries(name, dataset):
    collection = db["timeseries"]
    array_size = len(dataset)
    arr = np.asarray(dataset)
    flat = arr.ravel()
    array_size = int(flat.size)
    if np.issubdtype(flat.dtype, np.number):
        array_span = float(np.nanmax(flat) - np.nanmin(flat)) if array_size else 0.0
    else:
        array_span = None


    h = hashlib.sha256()
    h.update(name.encode())
    h.update(flat.tobytes())
    hash_id = h.hexdigest()

    timeseries_id = collection.insert_one({
        "name": name,
        "data": arr.tolist(),
        "created_at": datetime.now(),
        "array_size": array_size,
        "array_span": array_span,
        "hash_id": hash_id
    }).inserted_id
    return timeseries_id


####### IMAGE_COLLECTIONS #######

def check_existing_image(image: DataClass):
    collection = db["images"]

    existing = collection.find_one({"hash_id": image.hash_id})
    return existing

def create_image(image: DataClass, metadata={}):
    existing = check_existing_image(image)
    if existing is not None:
        return existing["_id"]

    collection = db["images"]

    if image.type not in ["image/png", "image/jpeg"]:
        raise ValueError("Only PNG and JPEG images are supported.")
    if image.type == "image/jpeg":
        image = convert_to_png(image)
        existing = check_existing_image(image)
        if existing is not None:
            return existing["_id"]


    image_id = put_file(image, metadata={"image_name": image.name})

    additional_metadata = extract_image_data(image)
    metadata.update(additional_metadata)

    img_doc_id = collection.insert_one({
        "name": image.name,
        "inserted_at": datetime.now(),
        "file_id": image_id,
        "hash_id": image.hash_id,
        "metadata": metadata
    }).inserted_id
    return img_doc_id

def create_image_collection(name, images: list[DataClass], metadata: dict = {}):
    # Create image collection even if it already exists a collection with the same name and set of images
    # The images are not going to be duplicated in the database
    # So it's acceptable to have multiple collections with the same images, but different names/metadata and
    # references to different sessions/print jobs

    collection = db["image_collections"]

    image_ids = [create_image(img) for img in images]

    coll_id = collection.insert_one({
        "name": name,
        "inserted_at": datetime.now(),
        "image_file_ids": image_ids,
        "metadata": metadata
    }).inserted_id
    return coll_id

def pass_session_to_image_collections(session_id, image_collection_ids: list):
    for coll_id in image_collection_ids:
        db["image_collections"].update_one(
            {"_id": coll_id},
            {"$set": {"session_id": session_id}}
        )


######## DICTIONARIES ########

def check_dictionary(printer, slicer):
    collection = db["dictionaries"]

    existing = collection.find_one({"printer": printer, "slicer": slicer})
    return existing

def get_dictionary(printer, slicer):
    collection = db["dictionaries"]

    existing = collection.find_one({"printer": printer, "slicer": slicer})
    if existing is not None:
        return existing["dict"], existing["_id"]
    
    # if it does not exist, create a new one

    dict_id = collection.insert_one({
        "printer": printer,
        "slicer": slicer,
        "dict": {},
        "created_at": datetime.now(),
    }).inserted_id
    return {}, dict_id

def get_all_existing_keys():
    d, _ = get_dictionary("", "")
    return list(d.keys())

def update_dictionary(dict_id, new_data: dict):
    collection = db["dictionaries"]

    existing = collection.find_one({"_id": dict_id})
    if existing is None:
        raise ValueError("Dictionary with the given ID does not exist.")

    collection.update_one(
        {"_id": dict_id},
        {"$set": {"dict": new_data}}
    )

def get_main_dictionary_id():
    collection = db["dictionaries"]

    existing = collection.find_one({"printer": "", "slicer": ""})
    if existing is not None:
        return existing["_id"], existing["dict"]
    else:
        dict_id = collection.insert_one({
            "printer": "",
            "slicer": "",
            "dict": {},
            "created_at": datetime.now(),
        }).inserted_id
        return collection.find_one({"_id": dict_id})


def append_to_main_dictionary(dict_input):
    collection = db["dictionaries"]

    main_dict_id, main_dict = get_main_dictionary_id()

    new_keys = dict_input.values()
    for k in new_keys:
        if k not in main_dict:
            main_dict[k] = k

    collection.update_one(
        {"_id": main_dict_id},
        {"$set": {"dict": main_dict}}
    )