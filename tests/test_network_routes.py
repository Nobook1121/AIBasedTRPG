import json

from trpg_server.app_factory import create_app
import trpg_server.network_discovery as network_discovery
from trpg_server.network_discovery import get_network_config, get_penetration_config


class FakeUserManager:
    def check_permission(self, user_id, required_role):
        return user_id == 1 and required_role == "ADMIN"


def _network_app(tmp_path, admin=True):
    app = create_app()
    app.config["USER_MANAGER"] = FakeUserManager()
    app.config["NETWORK_CONFIG_FILE"] = tmp_path / "network.json"
    app.config["PENETRATION_CONFIG_FILE"] = tmp_path / "penetration.json"
    client = app.test_client()
    if admin:
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "admin"
            session["role"] = "ADMIN"
    return client, app


def test_network_config_returns_default_when_file_is_missing(tmp_path):
    client, _ = _network_app(tmp_path, admin=False)

    response = client.get("/api/network/config")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["port"] == 8086
    assert data["data"]["discovery_enabled"] is True


def test_network_config_update_requires_admin(tmp_path):
    client, _ = _network_app(tmp_path, admin=False)

    response = client.post("/api/network/config", json={"port": 9000})

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_network_config_update_saves_file(tmp_path):
    client, app = _network_app(tmp_path)

    response = client.post(
        "/api/network/config",
        json={"port": 9000, "access_control": {"enabled": True, "allowed_ips": []}},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    saved = json.loads(app.config["NETWORK_CONFIG_FILE"].read_text(encoding="utf-8"))
    assert saved["port"] == 9000


def test_network_config_update_rejects_invalid_port(tmp_path):
    client, _ = _network_app(tmp_path)

    response = client.post("/api/network/config", json={"port": 70000})

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_penetration_config_update_and_status(tmp_path):
    client, app = _network_app(tmp_path)

    response = client.post(
        "/api/network/penetration/config",
        json={"enabled": True, "type": "frp", "settings": {"server": "example"}},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    saved = json.loads(app.config["PENETRATION_CONFIG_FILE"].read_text(encoding="utf-8"))
    assert saved["enabled"] is True

    status_response = client.get("/api/network/penetration/status")
    assert status_response.status_code == 200
    status = status_response.get_json()["data"]
    assert status["enabled"] is True
    assert status["type"] == "frp"


def test_default_network_config_returns_independent_nested_copy(tmp_path):
    missing_config = tmp_path / "missing-network.json"

    first = get_network_config(missing_config)
    first["access_control"]["allowed_ips"].append("127.0.0.1")

    second = get_network_config(missing_config)

    assert second["access_control"]["allowed_ips"] == []


def test_default_penetration_config_returns_independent_nested_copy(tmp_path):
    missing_config = tmp_path / "missing-penetration.json"

    first = get_penetration_config(missing_config)
    first["settings"]["auth_token"] = "changed"

    second = get_penetration_config(missing_config)

    assert second["settings"]["auth_token"] == ""


def test_get_local_ipv4_addresses_includes_hostname_addresses(monkeypatch):
    monkeypatch.setattr(network_discovery.socket, "gethostname", lambda: "host")
    monkeypatch.setattr(
        network_discovery.socket,
        "gethostbyname_ex",
        lambda hostname: (
            hostname,
            [],
            ["192.168.192.31", "192.168.0.169", "169.254.1.2", "127.0.0.1", "192.168.192.31"],
        ),
    )
    monkeypatch.setattr(network_discovery, "get_local_ip", lambda: "10.0.0.5")

    addresses = network_discovery.get_local_ipv4_addresses()

    assert addresses == ["127.0.0.1", "10.0.0.5", "192.168.192.31", "192.168.0.169"]
