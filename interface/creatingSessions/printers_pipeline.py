from database.serverHelper import create_printer

def printers_pipeline(printer_name, location="", description=""):
    printer_info = {
        "location": location,
        "description": description
    }

    printer_id = create_printer(printer_name, printer_info=printer_info)
    return printer_id