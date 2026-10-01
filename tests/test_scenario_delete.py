"""剧本删除后的权威性：向量/知识索引清理与列表隐藏。"""
from trpg_server.app_factory import create_app
from trpg_server.routes import scenarios as scenarios_module


class FakeManager:
    def __init__(self, role="ADMIN"):
        self.role = role

    def is_session_current(self, user_id, token):
        return True

    def get_user_by_id(self, user_id):
        return {"id": user_id, "username": "admin", "role": self.role}


def _app(tmp_path):
    return create_app({
        "TESTING": True,
        "USER_MANAGER": FakeManager("ADMIN"),
        "CONFIG_DIR": tmp_path / "config",
        "ROOMS_DIR": tmp_path / "rooms",
        "SCENARIOS_DIR": tmp_path / "scenarios",
        "EMBEDDED_VECTOR_DB_PATH": tmp_path / "vectors",
    })


def _login(client):
    with client.session_transaction() as session:
        session.update(user_id=1, username="tester", role="ADMIN", session_token="token", csrf_token="csrf")


def _create_scenario(client, title):
    return client.post(
        "/api/scenarios",
        json={
            "title": title,
            "author": "A",
            "playerCount": 2,
            "modules": [
                {"id": "scene", "module_type": "scene", "title": "Room", "summary": "room", "content": "secret room"},
                {"id": "end", "module_type": "ending", "title": "End", "summary": "end", "content": "done"},
            ],
        },
        headers={"X-CSRF-Token": "csrf"},
    )


def _isolate(tmp_path, monkeypatch):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", scenarios_dir)
    monkeypatch.setattr(scenarios_module, "SCENARIO_COVERS_DIR", tmp_path / "covers")
    return scenarios_dir


def test_delete_scenario_removes_vectors_and_list_entry(tmp_path, monkeypatch):
    app = _app(tmp_path)
    _isolate(tmp_path, monkeypatch)
    client = app.test_client()
    _login(client)

    created = _create_scenario(client, f"Deletable {tmp_path.name}")
    assert created.status_code == 201, created.get_json()
    scenario_id = created.get_json()["data"]["id"]
    vector_store = app.extensions["vector_store"]
    assert vector_store.count({"scenario_id": str(scenario_id)}) > 0

    deleted = client.delete(f"/api/scenarios/{scenario_id}", headers={"X-CSRF-Token": "csrf"})
    assert deleted.status_code == 200, deleted.get_json()

    # 删除必须同时清理知识库向量，否则已删除剧本仍可被检索。
    assert vector_store.count({"scenario_id": str(scenario_id)}) == 0

    listed = client.get("/api/scenarios").get_json()["data"]
    assert all(item["id"] != scenario_id for item in listed)


def test_archived_scenario_is_hidden_from_list(tmp_path, monkeypatch):
    app = _app(tmp_path)
    _isolate(tmp_path, monkeypatch)
    client = app.test_client()
    _login(client)

    created = _create_scenario(client, f"Archivable {tmp_path.name}")
    scenario_id = created.get_json()["data"]["id"]

    archived = client.post(f"/api/scenarios/{scenario_id}/archive", headers={"X-CSRF-Token": "csrf"})
    assert archived.status_code == 200, archived.get_json()

    # 归档（例如删除时仍有房间占用）的剧本不应再出现在列表中。
    listed = client.get("/api/scenarios").get_json()["data"]
    assert all(item["id"] != scenario_id for item in listed)
