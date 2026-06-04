from io import BytesIO

import trpg_server.routes.scenarios as scenario_routes
from trpg_server.app_factory import create_app


def _scenario_app(tmp_path, monkeypatch):
    scenarios_dir = tmp_path / "scenarios"
    covers_dir = tmp_path / "covers"
    scenarios_dir.mkdir()
    covers_dir.mkdir()

    monkeypatch.setattr(scenario_routes, "SCENARIOS_DIR", scenarios_dir)
    monkeypatch.setattr(scenario_routes, "SCENARIO_COVERS_DIR", covers_dir)
    scenario_routes.clear_scenarios_cache()

    return create_app(), scenarios_dir, covers_dir


def test_create_app_serves_index_page():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


def test_create_app_serves_avatar_with_no_cache_headers():
    app = create_app()
    client = app.test_client()

    response = client.get("/assets/avatars/default.jpg")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"


def test_create_app_lists_scenarios():
    app = create_app()
    client = app.test_client()

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_create_app_lists_scenario_files():
    app = create_app()
    client = app.test_client()

    response = client.get("/api/scenarios/list")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "files" in data["data"]
    assert "total" in data["data"]


def test_create_app_creates_scenario_file(tmp_path, monkeypatch):
    app, scenarios_dir, _ = _scenario_app(tmp_path, monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/scenarios",
        json={"title": "Camp One", "user_id": "u1"},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["title"] == "Camp One"
    assert (scenarios_dir / "Camp One.json").exists()


def test_create_app_updates_scenario_file(tmp_path, monkeypatch):
    app, scenarios_dir, _ = _scenario_app(tmp_path, monkeypatch)
    (scenarios_dir / "Old.json").write_text(
        '{"id": 12, "title": "Old", "createdAt": "2026-01-01T00:00:00.000Z"}',
        encoding="utf-8",
    )
    client = app.test_client()

    response = client.put(
        "/api/scenarios/12",
        json={"title": "New"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["id"] == 12
    assert data["data"]["title"] == "New"


def test_create_app_deletes_scenario_file_and_cover(tmp_path, monkeypatch):
    app, scenarios_dir, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (scenarios_dir / "Delete Me.json").write_text(
        '{"id": 42, "title": "Delete Me"}',
        encoding="utf-8",
    )
    cover_path = covers_dir / "42.png"
    cover_path.write_bytes(b"fake")
    client = app.test_client()

    response = client.delete("/api/scenarios/42", json={"user_id": "u1"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert not (scenarios_dir / "Delete Me.json").exists()
    assert not cover_path.exists()


def test_create_app_uploads_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/scenarios/cover",
        data={
            "scenario_title": "Camp One",
            "cover": (BytesIO(b"fake image"), "cover.png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["cover_url"] == "/assets/scenario_covers/Camp One.png"
    assert (covers_dir / "Camp One.png").exists()


def test_create_app_renames_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (covers_dir / "old.png").write_bytes(b"fake")
    client = app.test_client()

    response = client.post(
        "/api/scenarios/cover/rename",
        json={"old_filename": "old.png", "new_filename": "new.png"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert not (covers_dir / "old.png").exists()
    assert (covers_dir / "new.png").exists()


def test_create_app_deletes_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (covers_dir / "cover.png").write_bytes(b"fake")
    client = app.test_client()

    response = client.delete(
        "/api/scenarios/cover",
        json={"cover_path": "/assets/scenario_covers/cover.png"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert not (covers_dir / "cover.png").exists()
