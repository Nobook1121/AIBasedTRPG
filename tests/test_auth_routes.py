from trpg_server.app_factory import create_app


class FakeUserManager:
    def __init__(self):
        self.registered = None
        self.saved = False
        self.user = {
            "id": 7,
            "username": "alice",
            "role": "USER",
            "email": "alice@example.com",
            "avatar": "/assets/avatars/alice.png",
            "password": "old",
        }

    def register(self, username, password, email, ip_address=None):
        self.registered = {
            "username": username,
            "password": password,
            "email": email,
            "ip_address": ip_address,
        }
        return True, "registered"

    def login(self, username, password, ip_address=None):
        if username == "alice" and password == "secret":
            return True, "logged in", self.user
        return False, "invalid", None

    def get_user_by_id(self, user_id):
        if user_id == self.user["id"]:
            return self.user
        return None

    def _hash_password(self, password):
        return f"hashed:{password}"

    def _save_users(self):
        self.saved = True
        return True


def _auth_app():
    app = create_app()
    manager = FakeUserManager()
    app.config["USER_MANAGER"] = manager
    return app, manager


def test_auth_register_uses_configured_user_manager():
    app, manager = _auth_app()
    client = app.test_client()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "secret",
            "email": "alice@example.com",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert manager.registered["username"] == "alice"
    assert manager.registered["ip_address"] == "127.0.0.1"


def test_auth_login_sets_session_and_returns_user_data():
    app, _ = _auth_app()
    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user_id"] == 7
    with client.session_transaction() as session:
        assert session["user_id"] == 7
        assert session["username"] == "alice"
        assert session["role"] == "USER"


def test_auth_status_requires_login():
    app, _ = _auth_app()
    client = app.test_client()

    response = client.get("/api/auth/status")

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_auth_update_changes_profile_for_logged_in_user():
    app, manager = _auth_app()
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice2",
            "nickname": "Ali",
            "email": "alice2@example.com",
            "password": "new-secret",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["username"] == "alice2"
    assert manager.user["password"] == "hashed:new-secret"
    assert manager.saved is True
    with client.session_transaction() as session:
        assert session["username"] == "alice2"
