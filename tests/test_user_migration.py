import json
import sqlite3

import pytest

from trpg_server.users.database import UserDatabase
from trpg_server.users.migrations import migrate_json_users


def test_migrates_existing_json_users_to_sqlite(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "id": 7,
                        "username": "Alice",
                        "password": "hashed",
                        "email": "alice@example.com",
                        "role": "USER",
                        "status": "active",
                        "avatar": "/assets/avatars/a.png",
                        "nickname": "Ali",
                        "created_at": "2026-01-01T00:00:00.000Z",
                        "last_login": "2026-01-02T00:00:00.000Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    migrate_json_users(users_json, db)

    with db.connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = 7").fetchone()
        profile = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = 7"
        ).fetchone()
    assert user["username"] == "Alice"
    assert user["username_normalized"] == "alice"
    assert user["email_normalized"] == "alice@example.com"
    assert user["last_login_at"] == "2026-01-02T00:00:00.000Z"
    assert profile["nickname"] == "Ali"
    assert profile["avatar"] == "/assets/avatars/a.png"


def test_missing_json_users_file_does_not_error(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    migrate_json_users(tmp_path / "missing-users.json", db)

    with db.connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    assert count["count"] == 0


def test_skips_migration_when_users_table_already_has_rows(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "id": 7,
                        "username": "Alice",
                        "password": "hashed",
                        "email": "alice@example.com",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO users (
                id,
                username,
                username_normalized,
                email,
                email_normalized,
                password_hash
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                11,
                "Existing",
                "existing",
                "existing@example.com",
                "existing@example.com",
                "hash",
            ),
        )

    migrate_json_users(users_json, db)

    with db.connect() as conn:
        users = conn.execute("SELECT id, username FROM users ORDER BY id").fetchall()
    assert [(user["id"], user["username"]) for user in users] == [(11, "Existing")]


def test_migration_does_not_modify_original_json_file(tmp_path):
    users_json = tmp_path / "users.json"
    original_content = json.dumps(
        {
            "users": [
                {
                    "id": 7,
                    "username": "Alice",
                    "password": "hashed",
                    "email": "alice@example.com",
                }
            ]
        },
        indent=2,
    )
    users_json.write_text(original_content, encoding="utf-8")
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    migrate_json_users(users_json, db)

    assert users_json.read_text(encoding="utf-8") == original_content


def test_migration_normalizes_invalid_values_defaults_and_extra_profile(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "id": 8,
                        "username": "Bob",
                        "password": "hashed",
                        "email": "BOB@example.com",
                        "role": "GM",
                        "status": "deleted",
                        "bio": "ready",
                        "theme": "dark",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    migrate_json_users(users_json, db)

    with db.connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = 8").fetchone()
        profile = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = 8"
        ).fetchone()
    assert user["role"] == "USER"
    assert user["status"] == "active"
    assert user["email_normalized"] == "bob@example.com"
    assert profile["avatar"] == "/assets/avatars/default.jpg"
    assert profile["bio"] == "ready"
    assert json.loads(profile["profile_extra_json"]) == {"theme": "dark"}


def test_missing_required_legacy_user_field_raises_and_writes_no_user(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "id": 9,
                        "username": "   ",
                        "password": "hashed",
                        "email": "missing-username@example.com",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    with pytest.raises(ValueError, match="legacy user 9.*username"):
        migrate_json_users(users_json, db)

    assert _table_count(db, "users") == 0
    assert _table_count(db, "user_profiles") == 0


def test_non_object_legacy_user_raises_value_error(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text(json.dumps({"users": [None]}), encoding="utf-8")
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    with pytest.raises(ValueError, match="legacy user at index 0"):
        migrate_json_users(users_json, db)


def test_migration_rolls_back_entire_batch_when_later_user_fails(tmp_path):
    users_json = tmp_path / "users.json"
    users_json.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "id": 10,
                        "username": "Duplicate",
                        "password": "hashed-1",
                        "email": "first@example.com",
                    },
                    {
                        "id": 11,
                        "username": "duplicate",
                        "password": "hashed-2",
                        "email": "second@example.com",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    with pytest.raises(sqlite3.IntegrityError):
        migrate_json_users(users_json, db)

    assert _table_count(db, "users") == 0
    assert _table_count(db, "user_profiles") == 0


def _table_count(db, table_name):
    with db.connect() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return row["count"]
