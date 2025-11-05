# bachelor-thesis

Data Aggregation and Preparation for Machine Learning Algorithms in Additive Manufacturing / MEX context.



At the end, it's possible to see a complete description of each folder.

---

## Useful Commands

### 1) Environment setup

> If this is your first time, create and activate a virtual environment, then install the requirements.

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

> If you have already created the virtual environment before, you can skip the creation step and just activate it:

```bash
source venv/bin/activate
```

### 2) MongoDB (local)

You need a local MongoDB installation (see the official MongoDB installation guide for your OS).

On an external terminal, run:

```bash
mongod --dbpath /data/db
```

It is also possible to use a different data directory by changing the datapath after --dbpath.

### 3) Streamlit interfaces

```bash
PYTHONPATH=(...) streamlit run interface/creatingSessions/app.py
```

Replace `(...)` with the project root (or any additional paths your code needs).

### 4) Normal Python scripts

```bash
PYTHONPATH=(...) python3 path/to/script.py
```

### 5) Jupyter

Run notebooks directly in your Jupyter editor (e.g., the VS Code Jupyter extension).

---

## Server + Client

### Server

(You have to go for api/restapi/ folder to run this command)
```bash
PYTHONPATH=(...) python3 -m uvicorn server_restapi:app --reload --port 8000
```

It will probably ask you to run inside the folder
```bash
pip install uvicorn fastapi
```



### Client

Navigate to the desired folder and run the Python script normally:

```bash
PYTHONPATH=(...) python3 api/restapi/client_restapi.py
```

---

## Folder Structure

* **api** — Files related to API development proof-of-concepts (POCs).
* **data** — Test files. (Large example datasets, e.g., the one with 240 images, are excluded due to GitHub size limits.)
* **database** — Code related to database operations (backend ↔ MongoDB).
* **interface** — Python code for visuals / front-end.
  * Each subfolder contains the code for a single page.
* **scripts** — Python scripts used to run tests and proof-of-concepts.
* **uploads** — Can be ignored (temporary folder to handle `.zip` operations).
