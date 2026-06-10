from io import BytesIO

import trpg_server.routes.scenarios as scenario_routes
from trpg_server.app_factory import create_app
from trpg_server.security import SESSION_TOKEN_KEY
from trpg_server.users.passwords import hash_password
from trpg_server.users.service import UserService


def _scenario_app(tmp_path, monkeypatch):
    scenarios_dir = tmp_path / "scenarios"
    covers_dir = tmp_path / "covers"
    scenarios_dir.mkdir()
    covers_dir.mkdir()

    monkeypatch.setattr(scenario_routes, "SCENARIOS_DIR", scenarios_dir)
    monkeypatch.setattr(scenario_routes, "SCENARIO_COVERS_DIR", covers_dir)
    scenario_routes.clear_scenarios_cache()

    return create_app(), scenarios_dir, covers_dir


def _set_session(client, user_id=7, username="alice", role="USER"):
    manager = client.application.config["USER_MANAGER"]
    password = "StrongPass1"
    if hasattr(manager, "db"):
        with manager.db.connect() as connection:
            row = connection.execute(
                "SELECT id FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO users (
                        id,
                        username,
                        username_normalized,
                        email,
                        email_normalized,
                        password_hash,
                        role,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        username.lower(),
                        f"{username}{user_id}@example.com",
                        f"{username}{user_id}@example.com",
                        hash_password(password),
                        role,
                        "active",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO user_profiles (user_id, nickname, avatar, presence)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, username, "/assets/avatars/default.jpg", "online"),
                )
            else:
                connection.execute(
                    "UPDATE users SET role = ?, status = 'active' WHERE id = ?",
                    (role, user_id),
                )
        ok, message, user, token = manager.login(username, password)
        assert ok is True
    else:
        token = "test-token"
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["username"] = username
        session["role"] = role
        session[SESSION_TOKEN_KEY] = token


def test_create_app_serves_index_page():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


def test_create_app_configures_secure_session_cookie_defaults():
    app = create_app()

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_create_app_configures_request_body_size_limit():
    app = create_app()

    assert app.config["MAX_CONTENT_LENGTH"] == 4 * 1024 * 1024


def test_create_app_initializes_sqlite_user_service(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text('{"users": []}', encoding="utf-8")
    database_file = tmp_path / "users.sqlite3"

    app = create_app(
        {
            "USER_DATABASE_FILE": database_file,
            "USERS_FILE": users_json,
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
        }
    )

    assert isinstance(app.config["USER_MANAGER"], UserService)
    assert database_file.exists()


def test_create_app_skips_invalid_legacy_user_item_without_crashing(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text('{"users": [null]}', encoding="utf-8")
    database_file = tmp_path / "users.sqlite3"

    app = create_app(
        {
            "USER_DATABASE_FILE": database_file,
            "USERS_FILE": users_json,
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
        }
    )

    assert isinstance(app.config["USER_MANAGER"], UserService)
    assert database_file.exists()


def test_create_app_skips_duplicate_legacy_users_without_modifying_json(tmp_path):
    original_json = (
        '{"users": ['
        '{"id": 1, "username": "Alice", "password": "hash", "email": "a@example.com"},'
        '{"id": 2, "username": "alice", "password": "hash", "email": "b@example.com"}'
        ']}'
    )
    users_json = tmp_path / "users.json"
    users_json.write_text(original_json, encoding="utf-8")
    database_file = tmp_path / "users.sqlite3"

    app = create_app(
        {
            "USER_DATABASE_FILE": database_file,
            "USERS_FILE": users_json,
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
        }
    )

    assert isinstance(app.config["USER_MANAGER"], UserService)
    assert users_json.read_text(encoding="utf-8") == original_json


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
    _set_session(client)

    response = client.post(
        "/api/scenarios",
        json={"title": "Camp One", "user_id": "u1"},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["title"] == "Camp One"
    assert data["data"]["owner_id"] == 7
    assert (scenarios_dir / "Camp One.json").exists()


def test_create_app_rejects_unauthenticated_scenario_create(tmp_path, monkeypatch):
    app, _, _ = _scenario_app(tmp_path, monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/scenarios",
        json={"title": "Camp One", "user_id": "u1"},
    )

    assert response.status_code == 401


def test_create_app_normalizes_scenario_filename(tmp_path, monkeypatch):
    app, scenarios_dir, _ = _scenario_app(tmp_path, monkeypatch)
    client = app.test_client()
    _set_session(client)

    response = client.post(
        "/api/scenarios",
        json={"title": "../Escape", "user_id": "u1"},
    )

    assert response.status_code == 201
    assert (scenarios_dir / "Escape.json").exists()
    assert not (tmp_path / "Escape.json").exists()


def test_create_app_updates_scenario_file(tmp_path, monkeypatch):
    app, scenarios_dir, _ = _scenario_app(tmp_path, monkeypatch)
    (scenarios_dir / "Old.json").write_text(
        '{"id": 12, "title": "Old", "owner_id": 7, "createdAt": "2026-01-01T00:00:00.000Z"}',
        encoding="utf-8",
    )
    client = app.test_client()
    _set_session(client)

    response = client.put(
        "/api/scenarios/12",
        json={"title": "New"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["id"] == 12
    assert data["data"]["title"] == "New"


def test_create_app_rejects_scenario_update_from_non_owner(tmp_path, monkeypatch):
    app, scenarios_dir, _ = _scenario_app(tmp_path, monkeypatch)
    (scenarios_dir / "Old.json").write_text(
        '{"id": 12, "title": "Old", "owner_id": 7}',
        encoding="utf-8",
    )
    client = app.test_client()
    _set_session(client, user_id=8, username="bob")

    response = client.put(
        "/api/scenarios/12",
        json={"title": "New"},
    )

    assert response.status_code == 403


def test_create_app_deletes_scenario_file_and_cover(tmp_path, monkeypatch):
    app, scenarios_dir, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (scenarios_dir / "Delete Me.json").write_text(
        '{"id": 42, "title": "Delete Me", "owner_id": 7}',
        encoding="utf-8",
    )
    cover_path = covers_dir / "42.png"
    cover_path.write_bytes(b"fake")
    client = app.test_client()
    _set_session(client)

    response = client.delete("/api/scenarios/42", json={"user_id": "u1"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert not (scenarios_dir / "Delete Me.json").exists()
    assert not cover_path.exists()


def test_create_app_uploads_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    client = app.test_client()
    _set_session(client)

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
    assert data["data"]["cover_url"] == "/assets/scenario_covers/Camp%20One.png"
    assert (covers_dir / "Camp One.png").exists()


def test_create_app_normalizes_scenario_cover_filename(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    client = app.test_client()
    _set_session(client)

    response = client.post(
        "/api/scenarios/cover",
        data={
            "scenario_title": "../Escape",
            "cover": (BytesIO(b"fake image"), "cover.png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["data"]["cover_url"] == "/assets/scenario_covers/Escape.png"
    assert (covers_dir / "Escape.png").exists()
    assert not (tmp_path / "Escape.png").exists()


def test_create_app_renames_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (covers_dir / "old.png").write_bytes(b"fake")
    client = app.test_client()
    _set_session(client)

    response = client.post(
        "/api/scenarios/cover/rename",
        json={"old_filename": "old.png", "new_filename": "new.png"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert not (covers_dir / "old.png").exists()
    assert (covers_dir / "new.png").exists()


def test_create_app_renames_url_encoded_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (covers_dir / "Camp One.png").write_bytes(b"fake")
    client = app.test_client()
    _set_session(client)

    response = client.post(
        "/api/scenarios/cover/rename",
        json={"old_filename": "Camp%20One.png", "new_filename": "New Cover.png"},
    )

    assert response.status_code == 200
    assert not (covers_dir / "Camp One.png").exists()
    assert (covers_dir / "New Cover.png").exists()


def test_create_app_deletes_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (covers_dir / "cover.png").write_bytes(b"fake")
    client = app.test_client()
    _set_session(client)

    response = client.delete(
        "/api/scenarios/cover",
        json={"cover_path": "/assets/scenario_covers/cover.png"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert not (covers_dir / "cover.png").exists()


def test_create_app_deletes_url_encoded_scenario_cover(tmp_path, monkeypatch):
    app, _, covers_dir = _scenario_app(tmp_path, monkeypatch)
    (covers_dir / "Camp One.png").write_bytes(b"fake")
    client = app.test_client()
    _set_session(client)

    response = client.delete(
        "/api/scenarios/cover",
        json={"cover_path": "/assets/scenario_covers/Camp%20One.png"},
    )

    assert response.status_code == 200
    assert not (covers_dir / "Camp One.png").exists()
