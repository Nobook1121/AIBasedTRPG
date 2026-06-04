import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def temp_json_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"items": []}, ensure_ascii=False), encoding="utf-8")
    return path
