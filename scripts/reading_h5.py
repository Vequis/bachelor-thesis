import io
import h5py
import numpy as np
from scripts.classes.dataclass import DataClass

def extract_h5_datasets(data: DataClass):
    out = {}
    with h5py.File(io.BytesIO(data.bytes), "r") as f:
        def cb(name, obj):
            if isinstance(obj, h5py.Dataset):
                x = obj[()]
                if isinstance(x, bytes):
                    x = x.decode()
                elif isinstance(x, np.ndarray) and x.dtype.kind in ("S", "O"):
                    x = obj.asstr()[()]
                out[name] = x
        f.visititems(cb)
    return out

# data = extract_h5_datasets("data/h5/h5/3_power.h5")
# print(data["power_consumption"])
