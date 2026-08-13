import json
import os
import tempfile
from pathlib import Path


def read_json(path, default=None):
    json_path = Path(path)
    if not json_path.exists():
        return default

    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_atomic(path, data):
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    temp_file = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=json_path.parent,
        delete=False,
        suffix=".tmp",
    )
    temp_path = Path(temp_file.name)

    try:
        try:
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        finally:
            temp_file.close()

        os.replace(temp_path, json_path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
