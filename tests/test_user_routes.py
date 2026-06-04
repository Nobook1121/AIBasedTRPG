from trpg_server.app_factory import create_app


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
