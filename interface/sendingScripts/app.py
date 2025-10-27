import streamlit as st
import pandas as pd
import os, io, zipfile, uuid
from pathlib import Path
from datetime import datetime
from database.serverHelper import create_script
import uuid

from scripts.classes.dataclass import DataClass

st.set_page_config(page_title="Quick Upload", layout="wide")
st.title("Script Upload")

files = None

# --------------------------
# Session header (plain string + minimal persistence)
# --------------------------
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = str(uuid.uuid4())
if "file_buffer" not in st.session_state:
    st.session_state.file_buffer = []

def reset_uploader():
    # Clear the files by resetting the uploader key
    st.session_state["uploader_key"] = str(uuid.uuid4())
    st.session_state.file_buffer = []
    st.rerun()


# --------------------------
# Uploader
# --------------------------

def finish_script(file_buffer: list[DataClass]):
    for f in file_buffer:
        create_script(f)



with st.container():
    st.header("Upload files")
    files = st.file_uploader("Select a file", type=None, accept_multiple_files=True, key=st.session_state["uploader_key"])
    l, r = st.columns(2)
    if (files is not None and len(files) > 0 and files[0].name.lower().endswith(".py")):
        print(len(st.session_state.file_buffer), "files selected")
        if l.button("Finish upload", type="primary", width='stretch'):
            st.session_state.cur_session = None
            cur_session = None
            finish_script(st.session_state.file_buffer)
            reset_uploader()
        if r.button("Reset uploader (clear files)", type="secondary", width='stretch'):
            reset_uploader()


def handle_file(file: st.runtime.uploaded_file_manager.UploadedFile | Path):
    dc = DataClass(file) # dc = dataclass

    st.session_state.file_buffer.append(dc)

with st.container():
    if files:
        for file in files:
            if file.name.lower().endswith(".py"):
                handle_file(file)
            else:
                st.error(f"Unsupported file type: {file.name}. Only .py files are accepted.")
    else:
        st.info("Please upload a file.")
