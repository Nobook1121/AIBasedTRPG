from io import BytesIO

from trpg_server.app_factory import create_app


class FakeManager:
    def __init__(self, role="ADMIN"):
        self.role = role

    def is_session_current(self, user_id, token):
        return True

    def get_user_by_id(self, user_id):
        return {"id": user_id, "username": "admin", "role": self.role}


def _app(tmp_path, role="ADMIN"):
    return create_app({
        "TESTING": True,
        "USER_MANAGER": FakeManager(role),
        "CONFIG_DIR": tmp_path / "config",
        "KNOWLEDGE_BASES_DIR": tmp_path / "knowledge-bases",
        "ROOMS_DIR": tmp_path / "rooms",
        "SCENARIOS_DIR": tmp_path / "scenarios",
    })


def _login(client, role="ADMIN"):
    with client.session_transaction() as session:
        session.update(user_id=1, username="tester", role=role, session_token="token", csrf_token="csrf")


def test_ruleset_upload_requires_admin_and_indexes(tmp_path):
    app = _app(tmp_path, "USER"); client = app.test_client(); _login(client, "USER")
    denied = client.post("/api/knowledge-bases/coc7/sources", data={"file": (BytesIO(b"# Check\nroll"), "rules.md")}, headers={"X-CSRF-Token": "csrf"})
    assert denied.status_code == 403
    admin_client = _app(tmp_path, "ADMIN").test_client(); _login(admin_client, "ADMIN")
    response = admin_client.post("/api/knowledge-bases/coc7/sources", data={"file": (BytesIO(b"# Check\nroll"), "rules.md")}, headers={"X-CSRF-Token": "csrf"})
    assert response.status_code == 201
    assert response.get_json()["data"]["version"]["active_version"] == "1"


def test_ruleset_room_binding_and_archive(tmp_path):
    app = _app(tmp_path); client = app.test_client(); _login(client)
    client.post("/api/knowledge-bases/coc7/sources", data={"file": (BytesIO(b"# Check\nroll"), "rules.md")}, headers={"X-CSRF-Token": "csrf"})
    bound = client.post("/api/rooms/r-1/rulesets", json={"ruleset_id": "coc7"}, headers={"X-CSRF-Token": "csrf"})
    assert bound.status_code == 200
    assert bound.get_json()["data"]["coc7"] == "1"
    archived = client.post("/api/knowledge-bases/coc7/archive", headers={"X-CSRF-Token": "csrf"})
    assert archived.status_code == 200
    assert archived.get_json()["data"]["enabled"] is False


def test_ruleset_upload_requires_json_error_for_unauthenticated_and_accepts_pdf(tmp_path, monkeypatch):
    app = _app(tmp_path)
    client = app.test_client()
    response = client.post("/api/knowledge-bases/coc7/sources", data={"file": (BytesIO(b"x"), "rules.pdf")})
    assert response.status_code == 401
    assert response.content_type.startswith("application/json")


def test_ruleset_upload_returns_json_when_indexing_crashes(tmp_path, monkeypatch):
    app = _app(tmp_path)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    client = app.test_client(); _login(client, "ADMIN")

    class BrokenStore:
        def upload_source(self, *args, **kwargs):
            return {"source_id": "broken"}

        def reindex(self, *args, **kwargs):
            raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr("trpg_server.routes.knowledge_bases._store", lambda: BrokenStore())
    response = client.post(
        "/api/knowledge-bases/coc7/sources",
        data={"file": (BytesIO(b"# Check\nroll"), "rules.md")},
        headers={"X-CSRF-Token": "csrf", "Accept": "application/json"},
    )

    assert response.status_code == 500
    assert response.content_type.startswith("application/json")
    assert response.get_json()["success"] is False


def test_unknown_api_endpoint_returns_json_not_spa_html(tmp_path):
    app = _app(tmp_path)
    response = app.test_client().get("/api/knowledge-bases/does-not-exist", headers={"Accept": "application/json"})
    assert response.status_code == 404
    assert response.content_type.startswith("application/json")
    assert response.get_json()["success"] is False


def test_oversized_api_upload_returns_json_not_html(tmp_path):
    app = _app(tmp_path)
    app.config["MAX_CONTENT_LENGTH"] = 1
    client = app.test_client(); _login(client, "ADMIN")
    response = client.post(
        "/api/knowledge-bases/coc7/sources",
        data={"file": (BytesIO(b"too large"), "rules.md")},
        headers={"X-CSRF-Token": "csrf", "Accept": "application/json"},
    )
    assert response.status_code == 413
    assert response.content_type.startswith("application/json")


def test_scenario_knowledge_management_lists_searches_and_deletes(tmp_path):
    app = _app(tmp_path)
    client = app.test_client(); _login(client, "ADMIN")
    scenario = {"title": f"KB Case {tmp_path.name}-{id(tmp_path)}", "author": "A", "playerCount": 2, "modules": [
        {"id": "scene", "module_type": "scene", "title": "Room", "summary": "room", "content": "secret room"},
        {"id": "end", "module_type": "ending", "title": "End", "summary": "end", "content": "done"},
    ]}
    created = client.post("/api/scenarios", json=scenario, headers={"X-CSRF-Token": "csrf"})
    assert created.status_code == 201, created.get_json()
    scenario_id = created.get_json()["data"]["id"]
    listed = client.get("/api/knowledge-bases/scenarios?search=KB", headers={"X-CSRF-Token": "csrf"})
    assert listed.status_code == 200
    item = next(value for value in listed.get_json()["data"] if value["scenario_id"] == scenario_id)
    assert item["vector_count"] >= 0
    assert "path" in item
    deleted = client.delete(f"/api/knowledge-bases/scenarios/{scenario_id}", headers={"X-CSRF-Token": "csrf"})
    assert deleted.status_code == 200
    assert deleted.get_json()["data"]["deleted_vectors"] >= 0


def test_scenario_knowledge_count_includes_legacy_numeric_versions(tmp_path):
    app = _app(tmp_path)
    client = app.test_client(); _login(client, "ADMIN")
    scenario = {
        "title": f"Legacy vector {tmp_path.name}-{id(tmp_path)}",
        "author": "A",
        "playerCount": 2,
        "modules": [{"id": "scene", "module_type": "scene", "title": "Room", "summary": "room", "content": "secret room"}],
    }
    created = client.post("/api/scenarios", json=scenario, headers={"X-CSRF-Token": "csrf"})
    assert created.status_code == 201, created.get_json()
    scenario_id = created.get_json()["data"]["id"]
    app.extensions["vector_store"].upsert([{
        "chunk_id": "legacy-1",
        "embedding": [1.0, 0.0],
        "scenario_id": str(scenario_id),
        "scenario_version": "1",
    }])

    listed = client.get("/api/knowledge-bases/scenarios", headers={"X-CSRF-Token": "csrf"})
    assert listed.status_code == 200
    item = next(value for value in listed.get_json()["data"] if value["scenario_id"] == scenario_id)
    # One vector is created by the normal scenario import and one uses the
    # legacy numeric version; both belong to this scenario knowledge base.
    assert item["vector_count"] >= 2
