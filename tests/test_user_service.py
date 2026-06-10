from datetime import datetime, timezone

import bcrypt
import pytest

from trpg_server.users.database import UserDatabase
from trpg_server.users.passwords import verify_password
from trpg_server.users.service import UserService


def _service(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()
    return UserService(db)


def _latest_audit_event(service, user_id):
    with service.db.connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()


def _latest_session(service, user_id):
    with service.db.connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()


def test_register_requires_terms_and_unique_identity(tmp_path):
    service = _service(tmp_path)

    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=False,
    )
    assert ok is False
    assert "terms" in message.lower()

    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True
    assert user["username"] == "Alice"

    ok, message, user = service.register(
        "alice",
        "StrongPass1",
        "alice2@example.com",
        terms_accepted=True,
    )
    assert ok is False
    assert "Username already exists" in message

    ok, message, user = service.register(
        "Bob",
        "StrongPass1",
        "ALICE@example.com",
        terms_accepted=True,
    )
    assert ok is False
    assert "Email already exists" in message


@pytest.mark.parametrize("password", ["Pass1", "12345678", "password"])
def test_register_rejects_weak_password(tmp_path, password):
    service = _service(tmp_path)

    ok, message, user = service.register(
        "Alice",
        password,
        "alice@example.com",
        terms_accepted=True,
    )

    assert ok is False
    assert "password" in message.lower()
    assert user is None


def test_register_allows_username_rule_characters(tmp_path):
    service = _service(tmp_path)

    ok, message, user = service.register(
        "alice_ok-1.test",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )

    assert ok is True
    assert user["username"] == "alice_ok-1.test"


def test_register_rejects_invalid_username_and_email(tmp_path):
    service = _service(tmp_path)

    ok, message, user = service.register(
        "No Spaces",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is False
    assert "username" in message.lower()
    assert user is None

    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "not-an-email",
        terms_accepted=True,
    )
    assert ok is False
    assert "email" in message.lower()
    assert user is None


@pytest.mark.parametrize("username", ["ab", "a" * 33])
def test_register_rejects_username_length_boundaries(tmp_path, username):
    service = _service(tmp_path)

    ok, message, user = service.register(
        username,
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )

    assert ok is False
    assert "username" in message.lower()
    assert user is None


def test_register_creates_default_profile_and_audit_log(tmp_path):
    service = _service(tmp_path)

    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
        ip_address="127.0.0.1",
    )

    assert ok is True
    assert message == "User registered"
    with service.db.connect() as connection:
        profile = connection.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        audit_log = connection.execute(
            "SELECT * FROM audit_logs WHERE user_id = ?",
            (user["id"],),
        ).fetchone()

    assert profile["nickname"] == "Alice"
    assert profile["avatar"] == "/assets/avatars/default.jpg"
    assert profile["presence"] == "online"
    assert audit_log["event_type"] == "user_registered"
    assert audit_log["ip_address"] == "127.0.0.1"


def test_get_user_by_id_returns_public_user_with_profile_fields(tmp_path):
    service = _service(tmp_path)
    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True

    public_user = service.get_user_by_id(user["id"])

    assert public_user == {
        "id": user["id"],
        "username": "Alice",
        "email": "alice@example.com",
        "role": "USER",
        "nickname": "Alice",
        "avatar": "/assets/avatars/default.jpg",
        "presence": "online",
        "two_factor_enabled": False,
    }


def test_update_profile_rejects_duplicate_username_case_insensitive(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, bob = service.register(
        "Bob",
        "StrongPass1",
        "bob@example.com",
        terms_accepted=True,
    )
    assert ok is True

    ok, message = service.update_profile(
        bob["id"],
        username="ALICE",
        email="bob@example.com",
    )

    assert ok is False
    assert "Username already exists" in message


def test_update_profile_rejects_duplicate_email_case_insensitive(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, bob = service.register(
        "Bob",
        "StrongPass1",
        "bob@example.com",
        terms_accepted=True,
    )
    assert ok is True

    ok, message = service.update_profile(
        bob["id"],
        username="Bob",
        email="ALICE@example.com",
    )

    assert ok is False
    assert "Email already exists" in message


def test_update_profile_maps_username_integrity_error_to_duplicate_message(
    tmp_path,
    monkeypatch,
):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, bob = service.register(
        "Bob",
        "StrongPass1",
        "bob@example.com",
        terms_accepted=True,
    )
    assert ok is True
    monkeypatch.setattr(
        "trpg_server.users.service._identity_exists_for_other_user",
        lambda connection, column_name, normalized_value, user_id: False,
    )

    ok, message = service.update_profile(
        bob["id"],
        username="ALICE",
        email="bob@example.com",
    )

    assert ok is False
    assert message == "Username already exists"


def test_update_profile_maps_email_integrity_error_to_duplicate_message(
    tmp_path,
    monkeypatch,
):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, bob = service.register(
        "Bob",
        "StrongPass1",
        "bob@example.com",
        terms_accepted=True,
    )
    assert ok is True
    monkeypatch.setattr(
        "trpg_server.users.service._identity_exists_for_other_user",
        lambda connection, column_name, normalized_value, user_id: False,
    )

    ok, message = service.update_profile(
        bob["id"],
        username="Bob",
        email="ALICE@example.com",
    )

    assert ok is False
    assert message == "Email already exists"


def test_update_profile_rejects_password_change_without_current_password(tmp_path):
    service = _service(tmp_path)
    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True

    ok, message = service.update_profile(
        user["id"],
        username="Alice",
        email="alice@example.com",
        password="NewStrongPass1",
    )

    assert ok is False
    assert "password/change" in message
    ok, message, logged_in_user, token = service.login("Alice", "StrongPass1")
    assert ok is True
    ok, message, logged_in_user, token = service.login("Alice", "NewStrongPass1")
    assert ok is False


def test_register_hashes_password_and_verifies_it(tmp_path):
    service = _service(tmp_path)

    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )

    assert ok is True
    with service.db.connect() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()

    assert row["password_hash"] != "StrongPass1"
    assert row["password_hash"].startswith("$2")
    assert bcrypt.checkpw(b"StrongPass1", row["password_hash"].encode("utf-8"))
    assert verify_password("StrongPass1", row["password_hash"]) is True
    assert verify_password("WrongPass1", row["password_hash"]) is False


def test_login_accepts_email_and_revokes_previous_session(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)

    ok, message, user, first_token = service.login(
        "alice@example.com",
        "StrongPass1",
        ip_address="127.0.0.1",
    )
    assert ok is True
    ok, message, user, second_token = service.login(
        "Alice",
        "StrongPass1",
        ip_address="127.0.0.1",
    )
    assert ok is True

    assert service.is_session_current(user["id"], first_token) is False
    assert service.is_session_current(user["id"], second_token) is True


def test_login_rejects_wrong_password_and_writes_audit_log(tmp_path):
    service = _service(tmp_path)
    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True

    ok, message, user, token = service.login(
        "Alice",
        "WrongPass1",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert ok is False
    assert token is None
    assert user is None
    assert "password" in message.lower()
    audit_log = _latest_audit_event(service, 1)
    assert audit_log["event_type"] == "user_login_failed"
    assert audit_log["ip_address"] == "127.0.0.1"
    assert audit_log["user_agent"] == "pytest"


@pytest.mark.parametrize("status", ["banned", "inactive"])
def test_login_rejects_banned_or_inactive_user(tmp_path, status):
    service = _service(tmp_path)
    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True
    with service.db.connect() as connection:
        connection.execute(
            "UPDATE users SET status = ? WHERE id = ?",
            (status, user["id"]),
        )

    ok, message, user, token = service.login("Alice", "StrongPass1")

    assert ok is False
    assert user is None
    assert token is None
    assert status in message.lower()


def test_login_success_updates_last_login_and_writes_audit_log(tmp_path):
    service = _service(tmp_path)
    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True

    ok, message, user, token = service.login(
        "ALICE",
        "StrongPass1",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert ok is True
    assert token
    assert user["last_login_at"] is not None
    audit_log = _latest_audit_event(service, user["id"])
    assert audit_log["event_type"] == "user_login_success"
    assert audit_log["ip_address"] == "127.0.0.1"
    assert audit_log["user_agent"] == "pytest"


def test_login_stores_only_session_token_hash(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)

    ok, message, user, token = service.login("Alice", "StrongPass1")

    assert ok is True
    session = _latest_session(service, user["id"])
    assert session["session_token_hash"] != token
    assert token not in [value for value in dict(session).values() if value is not None]


def test_revoke_session_makes_session_not_current(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, user, token = service.login("Alice", "StrongPass1")
    assert ok is True

    service.revoke_session(user["id"], token)

    assert service.is_session_current(user["id"], token) is False


def test_touch_session_updates_current_session_last_seen_at(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, user, token = service.login("Alice", "StrongPass1")
    assert ok is True
    with service.db.connect() as connection:
        connection.execute(
            "UPDATE user_sessions SET last_seen_at = ? WHERE user_id = ?",
            ("2026-01-01T00:00:00+00:00", user["id"]),
        )

    touched = service.touch_session(user["id"], token)

    assert touched is True
    session = _latest_session(service, user["id"])
    assert session["last_seen_at"] != "2026-01-01T00:00:00+00:00"


def test_touch_session_rejects_none_token(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, user, token = service.login("Alice", "StrongPass1")
    assert ok is True

    assert service.touch_session(user["id"], None) is False


def test_touch_session_rejects_expired_session_without_precheck(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, user, token = service.login("Alice", "StrongPass1")
    assert ok is True
    original_last_seen = "2026-01-01T00:00:00+00:00"
    expired_at = "2026-01-02T00:00:00+00:00"
    with service.db.connect() as connection:
        connection.execute(
            """
            UPDATE user_sessions
            SET expires_at = ?,
                last_seen_at = ?
            WHERE user_id = ?
            """,
            (expired_at, original_last_seen, user["id"]),
        )

    def fail_precheck(user_id, session_token):
        pytest.fail("touch_session must enforce expiration in the UPDATE statement")

    monkeypatch.setattr(service, "is_session_current", fail_precheck)
    monkeypatch.setattr(
        "trpg_server.users.service._utc_now",
        lambda: datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    touched = service.touch_session(user["id"], token)

    assert touched is False
    session = _latest_session(service, user["id"])
    assert session["last_seen_at"] == original_last_seen


def test_touch_session_rejects_revoked_session(tmp_path):
    service = _service(tmp_path)
    service.register("Alice", "StrongPass1", "alice@example.com", terms_accepted=True)
    ok, message, user, token = service.login("Alice", "StrongPass1")
    assert ok is True
    service.revoke_session(user["id"], token)

    assert service.touch_session(user["id"], token) is False


def test_user_service_admin_user_methods_and_permissions(tmp_path):
    service = _service(tmp_path)
    ok, message, owner = service.register(
        "Owner",
        "StrongPass1",
        "owner@example.com",
        terms_accepted=True,
    )
    assert ok is True
    ok, message, user = service.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )
    assert ok is True
    with service.db.connect() as connection:
        connection.execute("UPDATE users SET role = 'OWNER' WHERE id = ?", (owner["id"],))

    users = service.get_all_users()
    assert {item["username"] for item in users} == {"Owner", "Alice"}
    assert service.check_permission(owner["id"], "ADMIN") is True
    assert service.check_permission(user["id"], "ADMIN") is False
    assert service.check_permission(owner["id"], "UNKNOWN") is False

    ok, message = service.update_user_role(user["id"], "ADMIN")
    assert ok is True
    ok, message = service.update_user_status(user["id"], "inactive")
    assert ok is True
    assert service.check_permission(user["id"], "USER") is False

    updated = service.get_user_by_id(user["id"])
    assert updated["role"] == "ADMIN"
    with service.db.connect() as connection:
        status = connection.execute(
            "SELECT status FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()["status"]
    assert status == "inactive"


def test_user_service_ip_config_methods(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()
    service = UserService(db, ip_config_dir=tmp_path / "ip_configs")

    assert service.get_ip_config("127.0.0.1") is None
    assert service.create_ip_config("127.0.0.1") is True

    config = service.get_ip_config("127.0.0.1")
    assert config["ip_address"] == "127.0.0.1"
    assert service.update_ip_config("127.0.0.1", {"settings": {"theme": "dark"}})
    assert service.get_ip_config("127.0.0.1")["settings"]["theme"] == "dark"
    assert len(service.get_all_ip_configs()) == 1
