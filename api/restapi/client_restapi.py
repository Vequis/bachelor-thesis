import requests
import json

BASE_URL = "http://localhost:8000"
SESSION_ID = "68fc08cd35cf3183635f4598"

r = requests.get(f"{BASE_URL}/get_session/{SESSION_ID}", timeout=30)
r.raise_for_status() # check for HTTP errors

data = r.json()

with open("session_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
