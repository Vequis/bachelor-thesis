from io import BytesIO
from PIL import Image, ExifTags
from scripts.classes.dataclass import DataClass

def extract_image_data(file_data):
    image = Image.open(BytesIO(file_data.bytes))
    width, height = image.size
    info = image.info
    exif = {}
    if hasattr(image, "_getexif") and image._getexif():
        exif = {ExifTags.TAGS.get(k, k): v for k, v in image._getexif().items()}
    return {
        "original_format": image.format,
        "mode": image.mode,
        "width": width,
        "height": height,
        "dpi": info.get("dpi"),
        "bit_depth": image.bits if hasattr(image, "bits") else None,
        "exif": exif,
    }

def run(args: list) -> dict:
    out = {}

    for dc in args:
        if type(dc) == DataClass and dc.type == "image/png":
            info = extract_image_data(dc)
            out[dc.name] = info

    return out
