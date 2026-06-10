from trpg_server.app_factory import create_app
from trpg_server.users.database import UserDatabase


class AuthSettingsManager:
    def __init__(self, db, admin=True):
        self.db = db
        self.admin = admin

    def check_permission(self, user_id, required_role):
        return self.admin and required_role == "ADMIN"


def _settings_app(tmp_path, admin=True):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()
    app = create_app()
    app.config["USER_MANAGER"] = AuthSettingsManager(db, admin=admin)
    client = app.test_client()
    return client, db


def _config_settings_app(admin=True):
    app = create_app()
    app.config["USER_MANAGER"] = AuthSettingsManager(db=None, admin=admin)
    client = app.test_client()
    return client


def _admin_session(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "ADMIN"


def test_password_reset_is_disabled_by_default(tmp_path):
    client, _ = _settings_app(tmp_path)

    response = client.post(
        "/api/auth/password/forgot",
        json={"identifier": "alice@example.com"},
    )

    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_email_verification_is_disabled_by_default(tmp_path):
    client, _ = _settings_app(tmp_path)

    response = client.post(
        "/api/auth/email/verify/request",
        json={"email": "alice@example.com"},
    )

    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_public_auth_settings_expose_enabled_flags_only(tmp_path):
    client, _ = _settings_app(tmp_path)

    response = client.get("/api/auth/settings")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["email_verification_enabled"] is False
    assert data["password_reset_enabled"] is False
    assert data["two_factor_enabled"] is False
    assert "smtp_enabled" not in data
    assert "smtp_configured" not in data
    assert "smtp_password" not in data


def test_auth_settings_requires_admin_for_update(tmp_path):
    client, _ = _settings_app(tmp_path)

    response = client.put(
        "/api/admin/auth/settings",
        json={"password_reset_enabled": True},
    )

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_admin_can_update_auth_settings_without_password_echo(tmp_path):
    client, db = _settings_app(tmp_path)
    _admin_session(client)

    response = client.put(
        "/api/admin/auth/settings",
        json={
            "password_reset_enabled": True,
            "smtp_enabled": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "mailer",
            "smtp_password": "secret",
            "smtp_from": "noreply@example.com",
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["password_reset_enabled"] is True
    assert data["smtp_enabled"] is True
    assert data["smtp_password_configured"] is True
    assert "smtp_password" not in data

    with db.connect() as connection:
        row = connection.execute("SELECT * FROM auth_settings WHERE id = 1").fetchone()
    assert row["password_reset_enabled"] == 1
    assert row["smtp_password"] == "secret"


def test_admin_auth_settings_update_uses_config_fallback_without_database():
    client = _config_settings_app()
    _admin_session(client)

    update_response = client.put(
        "/api/admin/auth/settings",
        json={"password_reset_enabled": True},
    )
    status_response = client.get("/api/auth/settings")

    assert update_response.status_code == 200
    assert status_response.get_json()["data"]["password_reset_enabled"] is True


def test_admin_auth_settings_rejects_non_boolean_feature_flags(tmp_path):
    client, db = _settings_app(tmp_path)
    _admin_session(client)

    response = client.put(
        "/api/admin/auth/settings",
        json={"password_reset_enabled": "false"},
    )

    assert response.status_code == 400
    with db.connect() as connection:
        row = connection.execute("SELECT * FROM auth_settings WHERE id = 1").fetchone()
    assert row is None or row["password_reset_enabled"] == 0


def test_admin_auth_settings_rejects_invalid_smtp_port(tmp_path):
    client, _ = _settings_app(tmp_path)
    _admin_session(client)

    bool_response = client.put("/api/admin/auth/settings", json={"smtp_port": True})
    float_response = client.put("/api/admin/auth/settings", json={"smtp_port": 25.9})
    list_response = client.put("/api/admin/auth/settings", json={"smtp_port": []})

    assert bool_response.status_code == 400
    assert float_response.status_code == 400
    assert list_response.status_code == 400


def test_password_reset_request_stays_disabled_until_setting_enabled(tmp_path):
    client, _ = _settings_app(tmp_path)
    _admin_session(client)
    client.put("/api/admin/auth/settings", json={"password_reset_enabled": True})

    response = client.post(
        "/api/auth/password/forgot",
        json={"identifier": "alice@example.com"},
    )

    assert response.status_code == 501
    assert response.get_json()["success"] is False
