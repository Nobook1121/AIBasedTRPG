import pytest

from trpg_server.json_store import read_json, write_json_atomic


def test_read_json_returns_default_for_missing_file(tmp_path):
    path = tmp_path / "missing.json"

    result = read_json(path, default={"items": []})

    assert result == {"items": []}


def test_write_json_atomic_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "data.json"

    write_json_atomic(path, {"name": "scenario"})

    assert read_json(path) == {"name": "scenario"}


def test_write_json_atomic_keeps_existing_file_and_removes_temp_when_json_dump_fails(tmp_path):
    path = tmp_path / "data.json"
    write_json_atomic(path, {"name": "old"})

    with pytest.raises(TypeError):
        write_json_atomic(path, {"bad": object()})

    assert read_json(path) == {"name": "old"}
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_json_atomic_keeps_existing_file_and_removes_temp_when_replace_fails(
    tmp_path, monkeypatch
):
    path = tmp_path / "data.json"
    write_json_atomic(path, {"name": "old"})

    def fail_replace(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr("trpg_server.json_store.os.replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        write_json_atomic(path, {"name": "new"})

    assert read_json(path) == {"name": "old"}
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_json_atomic_writes_utf8_content(tmp_path):
    path = tmp_path / "data.json"

    write_json_atomic(path, {"name": "scenario-\u957f\u751f"})

    decoded = path.read_bytes().decode("utf-8")
    assert "scenario-" in decoded
