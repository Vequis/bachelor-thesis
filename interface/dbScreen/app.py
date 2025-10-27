import streamlit as st

from database.serverHelper import download_files_zip, get_all_sessions

st.title("Sessions")

sessions = get_all_sessions()

for s in sessions:
    sid = str(s.get("_id", ""))
    n_files = len(s.get("raw_files", {}).get("file_ids", []))
    with st.expander(f"{sid} • raw_files: {n_files}"):
        st.json(s)
        if st.button("Generate ZIP", key=f"zip_{sid}"):
            zip_bytes = download_files_zip(s.get("raw_files", {}).get("file_ids", []))
            st.download_button("Download files", data=zip_bytes, file_name="files.zip", mime="application/zip", key=f"download_{sid}")