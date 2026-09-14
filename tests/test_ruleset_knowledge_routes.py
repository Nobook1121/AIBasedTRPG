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
