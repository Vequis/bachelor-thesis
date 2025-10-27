from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from bson import ObjectId, json_util
from database.serverHelper import get_session_with_embedded_info
import json

app = FastAPI()

# to run it, open a new terminal in this folder and run:
# PYTHONPATH=(PATH TO THE PROJECT FOLDER) uvicorn server_restapi:app --reload --port 8000

@app.get("/get_session/{session_id}")
def get_session(session_id: str):
    oid = ObjectId(session_id)
    result = get_session_with_embedded_info(oid)

    payload = json.loads(json_util.dumps(result))
    return JSONResponse(content=payload)
