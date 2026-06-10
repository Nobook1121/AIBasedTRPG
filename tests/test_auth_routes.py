from trpg_server.app_factory import create_app
import trpg_server.routes.auth as auth_routes
from io import BytesIO

import pytest

from trpg_server.security import SESSION_TOKEN_KEY
from trpg_server.users.database import UserDatabase
from trpg_server.users.passwords import hash_password, verify_password
from trpg_server.users.service import UserService


PNG_BYTES = b"\x89PNG\r\n\x1a\n"
JPEG_BYTES = b"\xff\xd8\xff\xe0"
GIF87A_BYTES = b"GIF87a"
GIF89A_BYTES = b"GIF89a"
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP"


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


class TokenUserManager(FakeUserManager):
    def __init__(self):
        super().__init__()
        self.revoked_session = None

    def login(self, username, password, ip_address=None):
        success, message, user = super().login(username, password, ip_address)
        return success, message, user, "service-token" if success else None

    def revoke_session(self, user_id, session_token):
        self.revoked_session = (user_id, session_token)
        return True


class NewStyleRegisterManager(FakeUserManager):
    def register(self, username, password, email, terms_accepted=False, ip_address=None):
        self.registered = {
            "username": username,
            "password": password,
            "email": email,
            "terms_accepted": terms_accepted,
            "ip_address": ip_address,
        }
        return True, "registered", self.user


class InternalTypeErrorRegisterManager(FakeUserManager):
    def __init__(self):
        super().__init__()
        self.new_style_calls = []
        self.legacy_calls = []

    def register(self, username, password, email, terms_accepted=False, ip_address=None):
        if ip_address is None and terms_accepted == "127.0.0.1":
            self.legacy_calls.append((username, password, email, terms_accepted))
            return True, "registered", self.user

        self.new_style_calls.append(
            {
                "username": username,
                "password": password,
                "email": email,
                "terms_accepted": terms_accepted,
                "ip_address": ip_address,
            }
        )
        raise TypeError("internal register bug")


class ServiceLikeLoginMissingTokenManager(FakeUserManager):
    def login(self, username, password, ip_address=None):
        success, message, user = super().login(username, password, ip_address)
        return success, message, user, None

    def is_session_current(self, user_id, token):
        return token == "service-token"


class FailingRevokeManager(TokenUserManager):
    def revoke_session(self, user_id, session_token):
        self.revoked_session = (user_id, session_token)
        raise RuntimeError("revoke failed")


class HashingLegacyPasswordManager(FakeUserManager):
    def __init__(self):
        super().__init__()
        self.user["password"] = hash_password("StrongPass1")

    def _hash_password(self, password):
        return hash_password(password)

    def _verify_password(self, password, password_hash):
        return verify_password(password, password_hash)


class FailingProfileUpdateManager(FakeUserManager):
    def update_profile(
        self,
        user_id,
        username,
        email,
        nickname="",
        avatar=None,
        password=None,
    ):
        return False, "Username already exists"


class RaisingProfileUpdateManager(FakeUserManager):
    def update_profile(
        self,
        user_id,
        username,
        email,
        nickname="",
        avatar=None,
        password=None,
    ):
        raise RuntimeError("profile update failed")


class ValueErrorProfileUpdateManager(FakeUserManager):
    def update_profile(
        self,
        user_id,
        username,
        email,
        nickname="",
        avatar=None,
        password=None,
    ):
        raise ValueError("invalid profile")


class RaisingSecondGetUserManager(FakeUserManager):
    def __init__(self):
        super().__init__()
        self.get_calls = 0

    def get_user_by_id(self, user_id):
        self.get_calls += 1
        if self.get_calls > 1:
            raise RuntimeError("cannot reload user")
        return super().get_user_by_id(user_id)


class RaisingLegacySaveManager(FakeUserManager):
    def _save_users(self):
        raise RuntimeError("save failed")


class FailingLegacySaveManager(FakeUserManager):
    def _save_users(self):
        return False


def _auth_app():
    app = create_app()
    manager = FakeUserManager()
    app.config["USER_MANAGER"] = manager
    return app, manager


def _service_auth_app(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()
    service = UserService(db)
    app = create_app()
    app.config["USER_MANAGER"] = service
    return app, service


def test_auth_register_uses_configured_user_manager():
    app, manager = _auth_app()
    client = app.test_client()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "secret",
            "confirm_password": "secret",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert manager.registered["username"] == "alice"
    assert manager.registered["ip_address"] == "127.0.0.1"


def test_auth_register_passes_terms_and_ip_to_new_style_manager():
    app = create_app()
    manager = NewStyleRegisterManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "secret",
            "confirm_password": "secret",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["success"] is True
    assert manager.registered == {
        "username": "alice",
        "password": "secret",
        "email": "alice@example.com",
        "terms_accepted": True,
        "ip_address": "127.0.0.1",
    }


def test_auth_register_internal_type_error_does_not_fallback_to_legacy_signature():
    app = create_app()
    manager = InternalTypeErrorRegisterManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "secret",
            "confirm_password": "secret",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert manager.new_style_calls == [
        {
            "username": "alice",
            "password": "secret",
            "email": "alice@example.com",
            "terms_accepted": True,
            "ip_address": "127.0.0.1",
        }
    ]
    assert manager.legacy_calls == []


def test_auth_register_rejects_unaccepted_terms():
    app, manager = _auth_app()
    client = app.test_client()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "secret",
            "confirm_password": "secret",
            "email": "alice@example.com",
            "terms_accepted": False,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert manager.registered is None


def test_auth_register_rejects_password_confirmation_mismatch():
    app, manager = _auth_app()
    client = app.test_client()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "secret",
            "confirm_password": "different",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert manager.registered is None


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
        assert "session_token" in session
        assert session.permanent is True


def test_auth_login_accepts_identifier_field():
    app, _ = _auth_app()
    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    with client.session_transaction() as session:
        assert session["user_id"] == 7


def test_auth_login_uses_manager_session_token_when_returned():
    app = create_app()
    manager = TokenUserManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    with client.session_transaction() as session:
        assert session[SESSION_TOKEN_KEY] == "service-token"


def test_auth_login_service_like_manager_requires_returned_session_token():
    app = create_app()
    manager = ServiceLikeLoginMissingTokenManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    with client.session_transaction() as session:
        assert SESSION_TOKEN_KEY not in session


def test_auth_login_allows_only_latest_session_for_same_account():
    app, _ = _auth_app()
    first_client = app.test_client()
    second_client = app.test_client()

    first_login = first_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret"},
    )
    second_login = second_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret"},
    )

    assert first_login.status_code == 200
    assert second_login.status_code == 200
    assert first_client.get("/api/auth/status").status_code == 401
    assert second_client.get("/api/auth/status").status_code == 200


def test_auth_status_returns_profile_fields_with_compatible_defaults():
    app, manager = _auth_app()
    manager.user.pop("nickname", None)
    manager.user.pop("presence", None)
    manager.user.pop("two_factor_enabled", None)
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.get("/api/auth/status")

    assert response.status_code == 200
    user_data = response.get_json()["data"]
    assert user_data == {
        "user_id": 7,
        "username": "alice",
        "role": "USER",
        "email": "alice@example.com",
        "avatar": "/assets/avatars/alice.png",
        "nickname": "alice",
        "presence": "online",
        "two_factor_enabled": False,
    }


def test_auth_status_requires_login():
    app, _ = _auth_app()
    client = app.test_client()

    response = client.get("/api/auth/status")

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_auth_logout_revokes_service_session_when_manager_supports_it():
    app = create_app()
    manager = TokenUserManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"
        session[SESSION_TOKEN_KEY] = "service-token"

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert manager.revoked_session == (7, "service-token")
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_auth_logout_clears_session_when_revoke_raises():
    app = create_app()
    manager = FailingRevokeManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"
        session[SESSION_TOKEN_KEY] = "service-token"

    response = client.post("/api/auth/logout")

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert manager.revoked_session == (7, "service-token")
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_auth_logout_clears_legacy_session_token(monkeypatch):
    app, _ = _auth_app()
    client = app.test_client()
    cleared = []
    monkeypatch.setattr(
        auth_routes,
        "clear_session_token",
        lambda user_id, token: cleared.append((user_id, token)),
    )
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"
        session[SESSION_TOKEN_KEY] = "legacy-token"

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert cleared == [(7, "legacy-token")]
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_auth_routes_work_with_real_user_service(tmp_path):
    app, service = _service_auth_app(tmp_path)
    client = app.test_client()

    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "Alice",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "StrongPass1"},
    )
    assert login_response.status_code == 200
    with client.session_transaction() as session:
        user_id = session["user_id"]
        session_token = session[SESSION_TOKEN_KEY]

    status_response = client.get("/api/auth/status")
    assert status_response.status_code == 200
    assert status_response.get_json()["data"]["nickname"] == "Alice"

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert service.is_session_current(user_id, session_token) is False
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_auth_update_with_real_user_service_updates_profile(tmp_path):
    app, service = _service_auth_app(tmp_path)
    client = app.test_client()
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "Alice",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "StrongPass1"},
    )
    assert login_response.status_code == 200

    response = client.post(
        "/api/auth/update",
        data={
            "username": "Alice2",
            "nickname": "Ali",
            "email": "alice2@example.com",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["username"] == "Alice2"
    assert data["data"]["email"] == "alice2@example.com"
    assert data["data"]["nickname"] == "Ali"
    with client.session_transaction() as session:
        assert session["username"] == "Alice2"
        user_id = session["user_id"]
    user = service.get_user_by_id(user_id)
    assert user["username"] == "Alice2"
    assert user["email"] == "alice2@example.com"
    assert user["nickname"] == "Ali"


def test_auth_update_with_real_user_service_rejects_password_field(tmp_path):
    app, service = _service_auth_app(tmp_path)
    client = app.test_client()
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "Alice",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "StrongPass1"},
    )
    assert login_response.status_code == 200

    with service.db.connect() as connection:
        before_hash = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            ("Alice",),
        ).fetchone()["password_hash"]

    response = client.post(
        "/api/auth/update",
        data={
            "username": "Alice",
            "nickname": "Ali",
            "email": "alice@example.com",
            "password": "NewStrongPass1",
        },
    )

    assert response.status_code == 400
    assert "password/change" in response.get_json()["message"]
    with service.db.connect() as connection:
        after_hash = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            ("Alice",),
        ).fetchone()["password_hash"]
    assert after_hash == before_hash

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    old_login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "StrongPass1"},
    )
    assert old_login_response.status_code == 200
    client.post("/api/auth/logout")
    new_login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "NewStrongPass1"},
    )
    assert new_login_response.status_code == 401


def test_auth_change_password_validates_current_password_and_updates_login(tmp_path):
    app, _ = _service_auth_app(tmp_path)
    client = app.test_client()
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "Alice",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
            "email": "alice@example.com",
            "terms_accepted": True,
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "StrongPass1"},
    )
    assert login_response.status_code == 200

    wrong_response = client.post(
        "/api/auth/password/change",
        json={"current_password": "WrongPass1", "new_password": "NewStrongPass1"},
    )
    assert wrong_response.status_code == 400

    response = client.post(
        "/api/auth/password/change",
        json={"current_password": "StrongPass1", "new_password": "NewStrongPass1"},
    )
    assert response.status_code == 200

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    old_login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "StrongPass1"},
    )
    assert old_login_response.status_code == 401
    new_login_response = client.post(
        "/api/auth/login",
        json={"identifier": "Alice", "password": "NewStrongPass1"},
    )
    assert new_login_response.status_code == 200


def test_auth_update_rejects_password_field_for_legacy_manager():
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

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "password/change" in data["message"]
    assert manager.user["username"] == "alice"
    assert manager.user["password"] == "old"
    assert manager.saved is False
    with client.session_transaction() as session:
        assert session["username"] == "alice"


def test_auth_update_changes_profile_for_logged_in_legacy_user_without_password():
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
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["username"] == "alice2"
    assert manager.user["password"] == "old"
    assert manager.saved is True
    with client.session_transaction() as session:
        assert session["username"] == "alice2"


def test_auth_change_password_legacy_manager_uses_hash_verifier():
    app = create_app()
    manager = HashingLegacyPasswordManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    wrong_response = client.post(
        "/api/auth/password/change",
        json={"current_password": "WrongPass1", "new_password": "NewStrongPass1"},
    )
    assert wrong_response.status_code == 400

    response = client.post(
        "/api/auth/password/change",
        json={"current_password": "StrongPass1", "new_password": "NewStrongPass1"},
    )

    assert response.status_code == 200
    assert verify_password("NewStrongPass1", manager.user["password"]) is True
    assert manager.saved is True


def test_auth_change_password_legacy_manager_rolls_back_when_save_fails():
    app = create_app()
    manager = FailingLegacySaveManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/password/change",
        json={"current_password": "old", "new_password": "NewStrongPass1"},
    )

    assert response.status_code == 500
    assert manager.user["password"] == "old"


def test_auth_update_normalizes_avatar_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app, manager = _auth_app()
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "../evil.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["data"]["avatar"].startswith("/assets/avatars/7_")
    assert data["data"]["avatar"].endswith("_evil.png")
    assert (tmp_path / "evil.png").exists() is False
    assert manager.saved is True


@pytest.mark.parametrize(
    ("payload", "filename", "content_type"),
    [
        (PNG_BYTES, "avatar.png", "image/png"),
        (JPEG_BYTES, "avatar.jpg", "image/jpeg"),
        (GIF87A_BYTES, "avatar.gif", "image/gif"),
        (GIF89A_BYTES, "avatar.gif", "image/gif"),
        (WEBP_BYTES, "avatar.webp", "image/webp"),
    ],
)
def test_auth_update_accepts_avatar_with_valid_signature(
    tmp_path,
    monkeypatch,
    payload,
    filename,
    content_type,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app, manager = _auth_app()
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(payload), filename, content_type),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    avatar_path = response.get_json()["data"]["avatar"]
    saved_filename = avatar_path.rsplit("/", 1)[1]
    assert (tmp_path / "avatars" / saved_filename).read_bytes() == payload
    assert manager.saved is True


def test_auth_update_rejects_avatar_with_disallowed_mime(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app, manager = _auth_app()
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(b"not an image"), "avatar.png", "text/plain"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert list((tmp_path / "avatars").glob("*")) == []
    assert manager.saved is False


def test_auth_update_rejects_avatar_with_spoofed_png_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app, manager = _auth_app()
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(b"not a real image"), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert list((tmp_path / "avatars").glob("*")) == []
    assert manager.saved is False


def test_auth_update_rejects_avatar_larger_than_two_mb_by_actual_bytes(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app, manager = _auth_app()
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (
                BytesIO(PNG_BYTES + b"x" * (2 * 1024 * 1024)),
                "avatar.png",
                "image/png",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert list((tmp_path / "avatars").glob("*")) == []
    assert manager.saved is False


def test_auth_update_removes_uploaded_avatar_when_profile_update_fails(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app = create_app()
    manager = FailingProfileUpdateManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "duplicate",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert list((tmp_path / "avatars").glob("*")) == []


def test_auth_update_removes_uploaded_avatar_when_profile_update_raises(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app = create_app()
    manager = RaisingProfileUpdateManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert list((tmp_path / "avatars").glob("*")) == []


def test_auth_update_removes_uploaded_avatar_when_profile_update_raises_value_error(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app = create_app()
    manager = ValueErrorProfileUpdateManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert list((tmp_path / "avatars").glob("*")) == []


def test_auth_update_keeps_uploaded_avatar_after_profile_update_succeeds(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app = create_app()
    manager = RaisingSecondGetUserManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    saved_files = list((tmp_path / "avatars").glob("*"))
    assert len(saved_files) == 1


def test_auth_update_removes_uploaded_avatar_when_legacy_save_raises(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app = create_app()
    manager = RaisingLegacySaveManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert list((tmp_path / "avatars").glob("*")) == []
    assert manager.user["avatar"] == "/assets/avatars/alice.png"


def test_auth_update_rolls_back_legacy_user_when_save_returns_false(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    app = create_app()
    manager = FailingLegacySaveManager()
    app.config["USER_MANAGER"] = manager
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    response = client.post(
        "/api/auth/update",
        data={
            "username": "alice2",
            "email": "alice2@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert list((tmp_path / "avatars").glob("*")) == []
    assert manager.user["username"] == "alice"
    assert manager.user["email"] == "alice@example.com"
    assert manager.user["avatar"] == "/assets/avatars/alice.png"


def test_auth_update_uses_unique_avatar_filename_with_same_second_uploads(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(auth_routes, "AVATARS_DIR", tmp_path / "avatars")
    monkeypatch.setattr(auth_routes.time, "time", lambda: 1234567890)
    app, _ = _auth_app()
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
        session["username"] = "alice"
        session["role"] = "USER"

    first = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )
    second = client.post(
        "/api/auth/update",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "avatar": (BytesIO(PNG_BYTES), "avatar.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()["data"]["avatar"] != second.get_json()["data"]["avatar"]
    assert len(list((tmp_path / "avatars").glob("*"))) == 2
