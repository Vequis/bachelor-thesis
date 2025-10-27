import importlib
from pathlib import Path

from bson import ObjectId

from database.serverHelper import download_file_as_dataclass, get_file_id_from_script
from scripts.classes.dataclass import DataClass

MODULES_PKG = "saved_modules"


def save(dc: DataClass) -> Path:
    folder = Path(MODULES_PKG)
    
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / dc.name
    with open(path, "wb") as f:
        f.write(dc.bytes)
    return path

def load_and_run_module(id: str, args: list = None, remove_after_run: bool = True) -> dict:
    oid = ObjectId(id)
    file_id = get_file_id_from_script(oid)
    if file_id is None:
        print(f"No file associated with script ID '{id}'")
        return {}

    args = args or []

    dc = download_file_as_dataclass(file_id)
    saved_path = save(dc)

    mod_name = saved_path.stem

    full_name = f"{MODULES_PKG}.{mod_name}"
    mod = importlib.import_module(full_name)

    if hasattr(mod, "run"):
        result = mod.run(args)
        print("Result(", mod_name, "):", result)
    else:
        print(f"Module '{mod_name}' has no 'run' function.")

    if remove_after_run and saved_path.exists():
        saved_path.unlink()

    return result

def load_example_png():
    data = Path("example_files/example.png")
    print(type(data))
    return DataClass(data=Path("example_files/example.png"))


if __name__ == "__main__":
    example_png = load_example_png()
    input_buffer = [ "StringExample", [1, 2, 3], [5, 12, 5], False, example_png ]

    dict_buffer_result = {}

    # This has to be defined manually for now
    scripts_to_run = [
        "68fcdca056cc35fbc525891b",
        "68fcddc956cc35fbc525891e"
    ]

    # Each module will return a dict
    for script_id in scripts_to_run:
        result = load_and_run_module(script_id, args=input_buffer, remove_after_run=True)
        dict_buffer_result.update(result)

    print()
    print("Final combined result from all modules:")
    print(dict_buffer_result)

    # load_and_run_module("68fac7d2238b7b243f7c4801", args=[1, 2, 3], remove_after_run=False)