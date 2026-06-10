import sqlite3

import pytest

from trpg_server.users.database import UserDatabase


def column_names(db, table_name):
    with db.connect() as connection:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()

    return {row["name"] for row in rows}


def test_user_database_initializes_required_tables(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    tables = db.table_names()

    assert {
        "users",
        "user_profiles",
        "user_sessions",
        "auth_settings",
        "email_verification_tokens",
        "password_reset_tokens",
        "audit_logs",
    }.issubset(tables)


def test_user_database_initializes_required_columns(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    assert {
        "username",
        "username_normalized",
        "email",
        "email_normalized",
        "password_hash",
        "role",
        "status",
        "last_login_at",
    }.issubset(column_names(db, "users"))
    profile_columns = column_names(db, "user_profiles")
    assert {
        "nickname",
        "avatar",
        "bio",
        "presence",
        "profile_extra_json",
    }.issubset(profile_columns)
    assert "display_name" not in profile_columns
    assert "avatar_url" not in profile_columns
    assert {
        "session_token_hash",
        "device_label",
        "ip_address",
        "user_agent",
        "last_seen_at",
    }.issubset(column_names(db, "user_sessions"))
    auth_settings_columns = column_names(db, "auth_settings")
    assert {
        "id",
        "email_verification_enabled",
        "password_reset_enabled",
        "two_factor_enabled",
        "smtp_enabled",
        "smtp_host",
        "smtp_port",
        "smtp_username",
        "smtp_password",
        "smtp_from",
        "created_at",
        "updated_at",
    }.issubset(auth_settings_columns)
    assert "user_id" not in auth_settings_columns


def test_user_role_and_status_constraints_use_design_values(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    with db.connect() as connection:
        connection.execute(
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
                "Owner",
                "owner",
                "owner@example.com",
                "owner@example.com",
                "hash",
                "OWNER",
                "banned",
            ),
        )

    with db.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO users (
                    username,
                    username_normalized,
                    email,
                    email_normalized,
                    password_hash,
                    role
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "Guest",
                    "guest",
                    "guest@example.com",
                    "guest@example.com",
                    "hash",
                    "GUEST",
                ),
            )

    with db.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO users (
                    username,
                    username_normalized,
                    email,
                    email_normalized,
                    password_hash,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "Deleted",
                    "deleted",
                    "deleted@example.com",
                    "deleted@example.com",
                    "hash",
                    "deleted",
                ),
            )


def test_user_normalized_username_and_email_are_unique(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    with db.connect() as connection:
        connection.execute(
            """
            INSERT INTO users (
                username,
                username_normalized,
                email,
                email_normalized,
                password_hash
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Alice",
                "alice",
                "alice@example.com",
                "alice@example.com",
                "hash",
            ),
        )

    with db.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO users (
                    username,
                    username_normalized,
                    email,
                    email_normalized,
                    password_hash
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Alice Duplicate",
                    "alice",
                    "alice2@example.com",
                    "alice2@example.com",
                    "hash",
                ),
            )

    with db.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO users (
                    username,
                    username_normalized,
                    email,
                    email_normalized,
                    password_hash
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Alice Email Duplicate",
                    "alice-email-duplicate",
                    "Alice@example.com",
                    "alice@example.com",
                    "hash",
                ),
            )


def test_user_sessions_allow_only_one_unrevoked_session_per_user(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    with db.connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username,
                username_normalized,
                email,
                email_normalized,
                password_hash
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Alice",
                "alice",
                "alice@example.com",
                "alice@example.com",
                "hash",
            ),
        )
        user_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO user_sessions (
                user_id,
                session_token_hash,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (user_id, "first-token-hash", "2026-01-08T00:00:00+00:00"),
        )

    with db.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO user_sessions (
                    user_id,
                    session_token_hash,
                    expires_at
                )
                VALUES (?, ?, ?)
                """,
                (user_id, "second-token-hash", "2026-01-08T00:00:00+00:00"),
            )

    with db.connect() as connection:
        connection.execute(
            """
            UPDATE user_sessions
            SET revoked_at = ?
            WHERE user_id = ?
            """,
            ("2026-01-02T00:00:00+00:00", user_id),
        )
        connection.execute(
            """
            INSERT INTO user_sessions (
                user_id,
                session_token_hash,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (user_id, "second-token-hash", "2026-01-08T00:00:00+00:00"),
        )

        active_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM user_sessions
            WHERE user_id = ?
                AND revoked_at IS NULL
            """,
            (user_id,),
        ).fetchone()[0]

    assert active_count == 1


def test_auth_settings_defaults_disable_auth_features(tmp_path):
    db = UserDatabase(tmp_path / "users.sqlite3")
    db.initialize()

    with db.connect() as connection:
        connection.execute("INSERT INTO auth_settings DEFAULT VALUES")
        row = connection.execute(
            """
            SELECT
                email_verification_enabled,
                password_reset_enabled,
                two_factor_enabled,
                smtp_enabled
            FROM auth_settings
            """
        ).fetchone()

    assert row["email_verification_enabled"] == 0
    assert row["password_reset_enabled"] == 0
    assert row["two_factor_enabled"] == 0
    assert row["smtp_enabled"] == 0
