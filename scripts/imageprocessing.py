from PIL import Image, ExifTags
from io import BytesIO
from scripts.classes.dataclass import DataClass


# Works (at least) for JPG and PNG formats
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


def convert_to_png(file_data):
    image = Image.open(BytesIO(file_data.bytes))
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return DataClass(data=output.getvalue(), mime_type="image/png", name=file_data.name.split(".")[0] + ".png")
