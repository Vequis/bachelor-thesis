import json
import numpy as np
from interface.creatingSessions.printers_pipeline import printers_pipeline
from scripts.reading_h5 import extract_h5_datasets
import streamlit as st
import pandas as pd
import os, io, zipfile, uuid
from pathlib import Path
from datetime import datetime
import uuid
from scripts.classes.dataclass import DataClass


from database.serverHelper import append_to_main_dictionary, create_image_collection, create_session, create_timeseries, get_all_existing_keys, get_dictionary, pass_session_to_image_collections, update_dictionary
from interface.creatingSessions.object_pipeline import object_pipeline
from interface.creatingSessions.print_job_pipeline import handle_gcode, print_job_pipeline

st.set_page_config(page_title="Quick Upload", layout="wide")
st.title("File Upload (CSV/XLSX/zip/...)")

files = None

ss = st.session_state

# --------------------------
# Session header (plain string + minimal persistence)
# --------------------------
if "cur_session" not in ss:
    ss.cur_session = None  # backing store
if "uploader_key" not in ss:
    ss["uploader_key"] = str(uuid.uuid4())
if "file_buffer" not in ss:
    ss.file_buffer = []
if "metadata_buffer" not in ss:
    ss.metadata_buffer = {}
if "print_job_buffer" not in ss:
    ss.print_job_buffer = None
if "datasets_buffer" not in ss:
    ss.datasets_buffer = {}
if "object_id" not in ss:
    ss.object_id = None
if "printer_id" not in ss:
    ss.printer_id = None
if "print_job_id" not in ss:
    ss.print_job_id = None
if "dict_id" not in ss:
    ss.dict_id = None
if "image_collections" not in st.session_state:
    st.session_state.image_collections = [] 
if "show_gcode" not in st.session_state:
    st.session_state.show_gcode = False
if "gcode_info" not in st.session_state:
    st.session_state.gcode_info = None

def reset_uploader():
    ss.uploader_key = str(uuid.uuid4())
    
    # Not working: 
    # if files is not None and len(files) > 0:
    #     st.success("Uploader reset. You can upload the same files again if needed.")

def _new_collection():
    cid = uuid.uuid4().hex[:8]
    return {
        "id": cid,
        "name": "",
        "files": [],
        "metadata_text": "{}",
    }


with st.container():
    header_placeholder = st.empty()
    header_placeholder.subheader(f"Current session: {ss.cur_session!r}")
    st.markdown("Use the controls below to set or create a new session.")
    col1, col2, col3 = st.columns([2, 1, 1])

    # Text input for a custom session name
    with col1:
        new_name = st.text_input("New session name", value="", placeholder="e.g., experiment-01")

        if st.button("Create with name"):
            # Basic normalization; adjust as needed
            name = new_name.strip() or None
            ss.cur_session = name
            st.success(f"Session set to: {name}")
            reset_uploader()
            st.rerun()

    # Create session with random name
    with col3:
        if st.button("Create random"):
            random_name = f"sess-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
            ss.cur_session = random_name
            st.success(f"Session set to: {random_name}")
            reset_uploader()
            st.rerun()

# --------------------------
# Printer_ID
# --------------------------
ss.printer_id = None
if ss.cur_session is not None:
    st.markdown("---")
    st.markdown("### Printer ID")
    ss.printer_id = st.text_input("Printer ID")
    st.write(f"Using Printer ID: {ss.printer_id!r}")

# --------------------------
# Uploader
# --------------------------

def finish_image_collections():
    image_collections_ids = []
    for coll in st.session_state.image_collections:
        try:
            metadata = json.loads(coll["metadata_text"]) if coll["metadata_text"].strip() else {}
        except Exception as e:
            st.error(f"Cannot create image collection {coll.get('name', '')!r}: invalid JSON metadata: {e}")
            continue

        image_collection_id = create_image_collection(
            name=coll.get("name", f"Collection-{uuid.uuid4().hex[:6]}"),
            images=[DataClass(f) for f in coll.get("files", [])],
            metadata=metadata
        )
        image_collections_ids.append(image_collection_id)

    return image_collections_ids


def finish_session_upload():
    # if ss.cur_session is not None and printer_id is not None and printer_id.strip() != "":
    printer_id = printers_pipeline(ss.printer_id)

    ss.object_id, file_ids = object_pipeline(st.session_state.file_buffer)

    print(printer_id)

    ss.print_job_id, _ = print_job_pipeline(ss.print_job_buffer, printer_id=ss.printer_id, object_id=ss.object_id)
    image_collections_ids = finish_image_collections()

    session_id, _ = create_session(st.session_state.file_buffer, metadata=st.session_state.metadata_buffer, print_job_id=ss.print_job_id, timeseries=ss.datasets_buffer or {}, image_collections_ids=image_collections_ids)
    st.write(f"Session {ss.cur_session!r} with {len(st.session_state.file_buffer)} files sent to server (simulated).")

    pass_session_to_image_collections(session_id, image_collections_ids)

    ss.cur_session = None
    ss.printer_id = None

number_of_imagecollections = 0
def clean_session_upload():
    ss.print_job_buffer = None
    reset_uploader()
    number_of_imagecollections = 0

    # Clean everything ideally (not implemented yet)
    st.rerun()


def show_imagecollection_wrappers():
    for idx, coll in enumerate(list(st.session_state.image_collections)):  # list() para permitir remoção no loop
        with st.expander(f"Collection #{idx+1}", expanded=False):
            coll["name"] = st.text_input(
                "Name",
                value=coll.get("name", ""),
                key=f"ic_name_{coll['id']}",
                placeholder="Collection Name"
            )

            uploaded_files = st.file_uploader(
                "Files",
                type=None,
                accept_multiple_files=True,
                key=f"ic_files_{coll['id']}"
            )
            if uploaded_files is not None:
                coll["files"] = uploaded_files

            # Metadados em JSON
            coll["metadata_text"] = st.text_area(
                "Metadata (JSON)",
                value=coll.get("metadata_text", ""),
                key=f"ic_md_{coll['id']}",
                height=160,
                placeholder='{"key": "value"}'
            )

            try:
                _ = json.loads(coll["metadata_text"]) if coll["metadata_text"].strip() else {}
            except Exception as e:
                # print(coll["metadata_text"])
                st.error(f"JSON invalid: {e}")

            c1, c2 = st.columns([1, 3])
            if c1.button("Remove", key=f"ic_rm_{coll['id']}", use_container_width=True):
                # remove esta coleção e refaz o render
                st.session_state.image_collections.pop(idx)
                st.rerun()

def show_gcode_fields_handler():
    if (files is not None and len(files) > 0):
        if st.button("Check GCode Fields", type="secondary", use_container_width=True):
            st.session_state.show_gcode = True
            st.session_state.gcode_info = None
            
        if st.session_state.show_gcode:
            # Search for GCode file
            # Assume only one GCode file for simplicity
            if st.session_state.get("gcode_info") is None:
                gcode_file = None
                for f in files:
                    if f.name.lower().endswith(".gcode"):
                        gcode_file = DataClass(f)
                        break
                if gcode_file is not None:
                    st.session_state.gcode_info = handle_gcode(gcode_file)

            if st.session_state.gcode_info is not None:
                gcode_info = st.session_state.get("gcode_info", {})
                slicer = gcode_info.get("Slicer", "Unknown")
                st.write(f"Detected slicer: **{slicer}**")
                st.write(f"Printer ID: **{ss.printer_id}**")

                dict_data, dict_id = get_dictionary(ss.printer_id, slicer)

                for k in gcode_info.keys():
                    if k not in dict_data:
                        dict_data[k] = k


                st.subheader("G-code Field Analysis")

                options = ["Define New One..."] + get_all_existing_keys()
                for k in dict_data.keys():
                    if k not in options:
                        options.append(k)

                # alphabetical order, keeping "Define New One..." at the top
                options = [options[0]] + sorted(options[1:])

                for k, v in dict_data.items():
                    c1, c2 = st.columns([1, 2])
                    c1.write(k)
                    idx = options.index(v) if v in options else len(options) - 1
                    sel = c2.selectbox("", options, index=idx, key=f"{k}_sel")
                    if sel == "Define New One...":
                        new = c2.text_input("New_value", value=v if v not in options else "", key=f"{k}_new")
                        dict_data[k] = new
                    else:
                        dict_data[k] = sel

                st.write(dict_data)

                if st.button("Save G-code Field Mapping", type="primary", use_container_width=True):
                    update_dictionary(dict_id, dict_data)
                    append_to_main_dictionary(dict_data)
                    st.success("G-code field mapping saved.")
                    st.session_state.show_gcode = False
                    st.session_state.gcode_info = None
                    st.rerun()
                # passar dict final pro print job pipeline
                # atualizar dict no DB
                # atualizar main_dict
            else:
                st.warning("No G-code file found among the uploaded files.")


if ss.cur_session is not None and ss.printer_id is not None and ss.printer_id.strip() != "":
    with st.container():
        st.markdown("---")
        st.header("Upload files")
        files = st.file_uploader("Select a file", type=None, accept_multiple_files=True, key=st.session_state["uploader_key"])
        st.caption("Hint: You can also upload a zip file containing multiple CSV/XLSX files.")

        show_gcode_fields_handler()

        st.subheader("Image Collections")
        show_imagecollection_wrappers()
        if st.button("Add Image Collection", type="secondary", use_container_width=True):
            st.session_state.image_collections.append(_new_collection())
            st.rerun()

        l, r = st.columns(2)
        if (files is not None and len(files) > 0):
            print(len(st.session_state.file_buffer), "files selected")
            if l.button("Finish session", type="primary", width='stretch'):
                finish_session_upload()
                clean_session_upload()
            if r.button("Reset uploader (clear files)", type="secondary", width='stretch'):
                clean_session_upload()

# Base save directory (optionally include session subdir)
save_root = Path("uploads")
# If you want to segregate by session, uncomment the next line:
# save_root = save_root / (ss.cur_session or "default")
save_root.mkdir(parents=True, exist_ok=True)

def numeric_preview(df: pd.DataFrame):
    """Show a preview of numeric columns if any exist."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if len(numeric_cols) >= 1:
        st.subheader("Numeric Columns Preview")
        st.dataframe(df[numeric_cols].head(50), use_container_width=True)
    else:
        st.info("No numeric columns found.")

def handle_spreadsheet(file: DataClass, save_path: Path):
    """
    Read CSV/XLS(X) either from an UploadedFile or a filesystem Path.
    Show a preview and numeric preview if applicable.
    """
    lower = file.name.lower()

    df = None

    if lower.endswith(".csv"):
        df = pd.read_csv(file)
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        df = pd.read_excel(file)

    if df is not None:
        st.subheader("Data Preview")
        st.dataframe(df.head(50), use_container_width=True)
        numeric_preview(df)

def handle_file(file: st.runtime.uploaded_file_manager.UploadedFile | Path):
    """
    Handle a single file (UploadedFile or Path).
    For spreadsheets, show previews; for others, simply acknowledge.
    """
    dc = DataClass(file) # dc = dataclass
    st.success(f"File received: {dc.name}")

    save_path = save_root / dc.name

    lower = dc.name.lower()
    if lower.endswith((".csv", ".xlsx", ".xls")):
        handle_spreadsheet(dc, save_path)
    elif lower.endswith(".zip"):
        handle_zip(dc)
    elif lower.endswith(".gcode"):
        ss.print_job_buffer = dc
        st.info("G-code file received. Metadata will be extracted when finalizing the print job.")
    elif lower.endswith(".h5"): 
        datasets = extract_h5_datasets(dc)
        ids = {}
        for name, v in datasets.items():
           if isinstance(v, np.ndarray):
                ids[name] = create_timeseries(name, v)

        # print(ids)
        ss.datasets_buffer = ids

    st.session_state.file_buffer.append(dc)
    # try:
    # except AttributeError:
    #     # In case file is a Path
    #     with open(file, "rb") as f:
    #         # st.write(f.read())
    #         st.session_state.file_buffer.append(f.read())

    # print(len(st.session_state.file_buffer), "files in buffer")
    # else:
    #     st.write("No preview available for this file type.")

def handle_zip(file: DataClass):
    """
    Extract a ZIP from an UploadedFile and call handle_file on each member.
    """
    if file.name.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(file.bytes)) as zf:
            for member in zf.infolist():
                # Skip directories
                if member.is_dir():
                    continue

                # Extract to a temp path preserving internal structure
                extracted_path = Path("temp") / member.filename
                extracted_path.parent.mkdir(parents=True, exist_ok=True)
                with open(extracted_path, "wb") as f:
                    f.write(zf.read(member))

                # Process the extracted file
                handle_file(extracted_path)


if ss.cur_session is not None and ss.printer_id is not None and ss.printer_id.strip() != "":
    with st.container():
        st.session_state.file_buffer = []
        for file in files:
                handle_file(file)
