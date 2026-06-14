from trpg_server.users.database import UserDatabase
from trpg_server.users.service import UserService


def _create_user(database, username, role):
    normalized = username.casefold()
    with database.connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username,
                username_normalized,
                email,
                email_normalized,
                password_hash,
                role,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                normalized,
                f"{normalized}@example.com",
                f"{normalized}@example.com",
                "unused-in-permission-test",
                role,
                "active",
            ),
        )
        return int(cursor.lastrowid)


def test_admin_permission_is_driven_by_persisted_role_not_username(tmp_path):
    database = UserDatabase(tmp_path / "users.sqlite3")
    database.initialize()
    service = UserService(database, tmp_path / "ip_configs")

    named_admin_id = _create_user(database, "ADMIN", "USER")
    role_admin_id = _create_user(database, "operator", "ADMIN")

    assert service.check_permission(named_admin_id, "ADMIN") is False
    assert service.check_permission(role_admin_id, "ADMIN") is True
