from trpg_server.app_factory import create_app
from trpg_server.security import SESSION_TOKEN_KEY
from trpg_server.users.database import UserDatabase
from trpg_server.users.service import UserService


class FakeUserManager:
    def __init__(self):
        self.role_updates = []
        self.status_updates = []
        self.ip_configs = {}
        self.users = [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "ADMIN",
                "created_at": "2026-01-01T00:00:00.000Z",
                "last_login": "2026-01-02T00:00:00.000Z",
                "status": "active",
                "password": "secret",
                "nickname": "Admin",
                "avatar": "/assets/avatars/default.jpg",
                "presence": "online",
                "two_factor_enabled": False,
            }
        ]

    def check_permission(self, user_id, required_role):
        return user_id == 1 and required_role == "ADMIN"

    def get_all_users(self):
        return self.users

    def update_user_role(self, user_id, role):
        self.role_updates.append((user_id, role))
        return True, "role updated"

    def update_user_status(self, user_id, status):
        self.status_updates.append((user_id, status))
        return True, "status updated"

    def get_ip_config(self, ip_address):
        return self.ip_configs.get(ip_address)

    def create_ip_config(self, ip_address):
        self.ip_configs[ip_address] = {
            "ip_address": ip_address,
            "settings": {},
            "preferences": {},
        }
        return True

    def update_ip_config(self, ip_address, config_data):
        if ip_address not in self.ip_configs:
            self.create_ip_config(ip_address)
        self.ip_configs[ip_address].update(config_data)
        return True

    def get_all_ip_configs(self):
        return list(self.ip_configs.values())

    def get_user_by_id(self, user_id):
        for user in self.users:
            if user["id"] == user_id:
                return user
        return None

    def update_profile(
        self,
        user_id,
        username,
        email,
        nickname="",
        avatar=None,
        password=None,
    ):
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        user["username"] = username
        user["email"] = email
        user["nickname"] = nickname
        if avatar is not None:
            user["avatar"] = avatar
        return True, "Profile updated"

    def update_presence(self, user_id, presence):
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        if presence not in {"online", "dnd", "invisible"}:
            return False, "Invalid presence"
        user["presence"] = presence
        return True, "Presence updated"


class FailingLegacyUserManager:
    def __init__(self):
        self.user = {
            "id": 7,
            "username": "alice",
            "email": "alice@example.com",
            "role": "USER",
            "status": "active",
            "created_at": "2026-01-01T00:00:00.000Z",
            "last_login": "2026-01-02T00:00:00.000Z",
            "nickname": "Alice",
            "avatar": "/assets/avatars/alice.png",
            "presence": "online",
            "two_factor_enabled": False,
        }

    def get_user_by_id(self, user_id):
        if user_id == self.user["id"]:
            return self.user
        return None

    def _save_users(self):
        return False


def _user_app(admin=True):
    app = create_app()
    manager = FakeUserManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    if admin:
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "admin"
            session["role"] = "ADMIN"
    return client, manager


def _service_user_app(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()
    service = UserService(db)
    app = create_app()
    app.config["USER_MANAGER"] = service
    client = app.test_client()
    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True
    ok, message, login_user, token = service.login("Alice", "StrongPass1")
    assert ok is True
    with client.session_transaction() as session:
        session["user_id"] = login_user["id"]
        session["username"] = login_user["username"]
        session["role"] = login_user["role"]
        session[SESSION_TOKEN_KEY] = token
    return client, service, login_user


def test_users_route_requires_admin_session():
    client, _ = _user_app(admin=False)

    response = client.get("/api/users")

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_users_route_filters_sensitive_fields():
    client, _ = _user_app()

    response = client.get("/api/users")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"][0]["username"] == "admin"
    assert "password" not in data["data"][0]


def test_users_route_updates_role():
    client, manager = _user_app()

    response = client.put("/api/users/2/role", json={"role": "USER"})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert manager.role_updates == [(2, "USER")]


def test_user_profile_requires_login():
    client, _ = _user_app(admin=False)

    response = client.get("/api/user/profile")

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_user_profile_returns_current_profile_for_logged_in_user(tmp_path):
    client, _, user = _service_user_app(tmp_path)

    response = client.get("/api/user/profile")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["user_id"] == user["id"]
    assert data["username"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert data["nickname"] == "Alice"
    assert data["avatar"] == "/assets/avatars/default.jpg"
    assert data["presence"] == "online"
    assert data["two_factor_enabled"] is False
    assert "password_hash" not in data


def test_user_profile_updates_current_profile(tmp_path):
    client, service, user = _service_user_app(tmp_path)

    response = client.put(
        "/api/user/profile",
        json={
            "username": "Alice2",
            "email": "alice2@example.com",
            "nickname": "Ali",
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["username"] == "Alice2"
    assert data["email"] == "alice2@example.com"
    assert data["nickname"] == "Ali"
    assert service.get_user_by_id(user["id"])["nickname"] == "Ali"


def test_user_presence_accepts_dnd(tmp_path):
    client, service, user = _service_user_app(tmp_path)

    response = client.put("/api/user/presence", json={"presence": "dnd"})

    assert response.status_code == 200
    assert response.get_json()["data"]["presence"] == "dnd"
    assert service.get_user_by_id(user["id"])["presence"] == "dnd"


def test_user_presence_rejects_invalid_value(tmp_path):
    client, service, user = _service_user_app(tmp_path)

    response = client.put("/api/user/presence", json={"presence": "away"})

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert service.get_user_by_id(user["id"])["presence"] == "online"


def test_user_profile_legacy_fallback_rolls_back_when_save_fails():
    app = create_app()
    manager = FailingLegacyUserManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.put(
        "/api/user/profile",
        json={
            "username": "alice2",
            "email": "alice2@example.com",
            "nickname": "Alice2",
            "avatar": "/assets/avatars/new.png",
        },
    )

    assert response.status_code == 500
    assert manager.user["username"] == "alice"
    assert manager.user["email"] == "alice@example.com"
    assert manager.user["nickname"] == "Alice"
    assert manager.user["avatar"] == "/assets/avatars/alice.png"


def test_user_presence_legacy_fallback_rolls_back_when_save_fails():
    app = create_app()
    manager = FailingLegacyUserManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.put("/api/user/presence", json={"presence": "dnd"})

    assert response.status_code == 500
    assert manager.user["presence"] == "online"


def test_user_ip_config_get_creates_missing_config():
    client, manager = _user_app(admin=False)

    response = client.get("/api/user/ip/config")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["ip_address"] == "127.0.0.1"
    assert "127.0.0.1" in manager.ip_configs


def test_admin_ip_configs_requires_permission():
    client, manager = _user_app()
    manager.create_ip_config("127.0.0.1")

    response = client.get("/api/admin/ip/configs")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"][0]["ip_address"] == "127.0.0.1"
