import mimetypes
from pathlib import Path
from streamlit.runtime.uploaded_file_manager import UploadedFile
import hashlib

class DataClass:
    def __init__(self, data: UploadedFile | Path | bytes, mime_type: str = None, name: str = None):
        if type(data) == UploadedFile:
            self.name = name or data.name
            self.type = data.type
            self.size = data.size
            self.bytes = data.read()
            self.hash_id = hashlib.sha256(self.bytes).hexdigest()
        elif isinstance(data, Path):
            self.name = name or data.name
            self.type = mimetypes.guess_type(data.name)[0] or "application/octet-stream"
            self.size = data.stat().st_size
            with open(data, "rb") as f:
                self.bytes = f.read()

            self.hash_id = hashlib.sha256(self.bytes).hexdigest()
        elif type(data) == bytes:
            self.name = name or "unknown"
            self.type = mime_type or "application/octet-stream"
            self.size = len(data)
            self.bytes = data
            self.hash_id = hashlib.sha256(self.bytes).hexdigest()
        else:
            raise ValueError("Data must be an UploadedFile or Path or bytes")

    