from database.serverHelper import create_object

def object_pipeline(file_datas): 
    # file_datas is a list of file-like objects
    extracted_data = {}

    # Extract information from .3mf, .stl, etc
    # ...
    # ...

    object_id, file_ids = create_object(file_datas, extracted_data)
    return object_id, file_ids