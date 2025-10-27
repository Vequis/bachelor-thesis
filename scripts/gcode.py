from tabulate import tabulate

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def is_percentage(s):
    if s.endswith('%'):
        try:
            float(s[:-1])
            return True
        except ValueError:
            return False
    return False

def is_json(s):
    s = s.strip()
    return (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']'))

def convert_value(value):
    if is_integer(value):
        return int(value)
    elif is_number(value):
        return float(value)
    elif is_percentage(value):
        return float(value[:-1]) / 100.0
    elif is_json(value):
        import json
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value

def extract_gcode(file_path: str) -> dict:
    info = {}
    is_thumbnail = False

    with open(file_path, "r", encoding="ascii", errors="ignore") as f:
        for line in f:
            # print(line)
            # print()
            if line.startswith("; thumbnail_QOI begin"):
                is_thumbnail = True
            if line.startswith("; thumbnail_QOI end"):
                is_thumbnail = False
            if is_thumbnail:
                continue

            line = line.strip()
            if line.startswith(";") and "=" in line:
                line = line[1:].strip()
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                info[key] = convert_value(value)
                # info[key] = value

    return info

if __name__ == "__main__":

    file_pathz = "/home/vitor/Desktop/TUD/Bachelor/processing/data/Keychain_Dual_Color_QOI_0.4n_0.2mm_PLA_COREONE_9m.gcode"

    info = extract_gcode(file_pathz)

    # print('a', info["bed_temperature"], 'a')

    table = [[k, type(v), v] for k, v in info.items()]

    print(len(info.items()))

    print(tabulate(table, headers=["Parâmetro", "Tipo", "Valor"], tablefmt="pretty"))