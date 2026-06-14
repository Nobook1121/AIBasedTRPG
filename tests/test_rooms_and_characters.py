import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trpg_server.app_factory import create_app


def _app(tmp_path):
    characters_dir = tmp_path / "characters"
    characters_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "general.toml").write_text("[character_rules]\nmax_cards_per_user = 5\n", encoding="utf-8")
    (characters_dir / "sample-investigator.json").write_text(
        json.dumps({"id": "sample-investigator", "name": "Sample", "playerId": ""}),
        encoding="utf-8",
    )
    return create_app(
        {
            "TESTING": True,
            "USER_DATABASE_FILE": tmp_path / "users.sqlite3",
            "USERS_FILE": tmp_path / "users.json",
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
            "LOGS_DIR": tmp_path / "logs",
            "ROOMS_DIR": tmp_path / "rooms",
            "CHARACTERS_DIR": characters_dir,
            "CONFIG_DIR": config_dir,
        }
    )


def _login(client, user_id=1, username="alice", role="USER"):
    database_path = Path(client.application.config["USER_DATABASE_FILE"])
    with __import__("sqlite3").connect(database_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO users (
                id,
                username,
                username_normalized,
                email,
                email_normalized,
                password_hash,
                role,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                username.casefold(),
                f"{username.casefold()}@example.com",
                f"{username.casefold()}@example.com",
                "unused",
                role,
                "active",
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO user_sessions (
                user_id,
                session_token_hash,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                hashlib.sha256(f"test-token-{user_id}".encode("utf-8")).hexdigest(),
                (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            ),
        )
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["username"] = username
        session["role"] = role
        session["session_token"] = f"test-token-{user_id}"


def _room_payload(name="Room"):
    return {"name": name, "scenario_id": 1, "scenario_title": "Scenario"}


def test_room_creation_no_longer_requires_character_card(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client)

    response = client.post("/api/rooms", json=_room_payload())

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert "character_card" not in data["members"][0]


def test_room_character_binding_requires_own_character_for_regular_user(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client)
    room = client.post("/api/rooms", json=_room_payload()).get_json()["data"]
    user_id = str(room["members"][0]["user_id"])

    public_card = {"id": "sample-investigator", "name": "Sample", "playerId": ""}
    rejected = client.put(f"/api/rooms/{room['id']}/members/{user_id}/character", json={"character_card": public_card})
    owned = client.put(
        f"/api/rooms/{room['id']}/members/{user_id}/character",
        json={"character_card": {"id": "owned", "name": "Owned", "playerId": "1"}},
    )

    assert rejected.status_code == 403
    assert owned.status_code == 200
    assert owned.get_json()["data"]["members"][0]["character_card"]["id"] == "owned"


def test_character_api_lists_public_and_owned_cards(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client)

    client.put("/api/characters/owned", json={"id": "owned", "name": "Owned", "playerId": "1"})
    response = client.get("/api/characters")

    assert response.status_code == 200
    ids = {card["id"] for card in response.get_json()["data"]}
    assert {"sample-investigator", "owned"}.issubset(ids)


def test_regular_user_character_card_limit_is_configurable(tmp_path):
    client = _app(tmp_path).test_client()
    config_dir = Path(client.application.config["CONFIG_DIR"])
    (config_dir / "general.toml").write_text("[character_rules]\nmax_cards_per_user = 2\n", encoding="utf-8")
    _login(client)

    first = client.put("/api/characters/owned-1", json={"id": "owned-1", "name": "Owned 1", "playerId": "1"})
    second = client.put("/api/characters/owned-2", json={"id": "owned-2", "name": "Owned 2", "playerId": "1"})
    third = client.put("/api/characters/owned-3", json={"id": "owned-3", "name": "Owned 3", "playerId": "1"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 403


def test_admin_character_card_limit_is_unlimited(tmp_path):
    client = _app(tmp_path).test_client()
    config_dir = Path(client.application.config["CONFIG_DIR"])
    (config_dir / "general.toml").write_text("[character_rules]\nmax_cards_per_user = 1\n", encoding="utf-8")
    _login(client, role="ADMIN")

    for index in range(3):
        response = client.put(
            f"/api/characters/admin-{index}",
            json={"id": f"admin-{index}", "name": f"Admin {index}", "playerId": "1"},
        )
        assert response.status_code == 200


def test_admin_can_unbind_and_reassign_character_card_owner(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client, user_id=9, username="ADMIN", role="ADMIN")

    created = client.put(
        "/api/characters/admin-card",
        json={"id": "admin-card", "name": "Admin Card", "playerId": "9"},
    )
    unbound = client.put(
        "/api/characters/admin-card",
        json={"id": "admin-card", "name": "Admin Card", "playerId": ""},
    )
    reassigned = client.put(
        "/api/characters/admin-card",
        json={"id": "admin-card", "name": "Admin Card", "playerId": "2"},
    )

    assert created.status_code == 200
    assert created.get_json()["data"]["playerId"] == "9"
    assert unbound.status_code == 200
    assert unbound.get_json()["data"]["playerId"] == ""
    assert reassigned.status_code == 200
    assert reassigned.get_json()["data"]["playerId"] == "2"


def test_removed_room_member_is_kept_as_history_and_can_rejoin(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client, user_id=1, username="owner")
    room = client.post("/api/rooms", json=_room_payload()).get_json()["data"]

    _login(client, user_id=2, username="player")
    joined = client.post("/api/rooms/join", json={"room_code": room["room_code"]}).get_json()["data"]
    assert len(joined["members"]) == 2

    _login(client, user_id=1, username="owner")
    removed = client.delete(f"/api/rooms/{room['id']}/members/2")

    assert removed.status_code == 200
    members = removed.get_json()["data"]["members"]
    player = next(member for member in members if str(member["user_id"]) == "2")
    assert player["is_active"] is False
    assert player["status"] == "removed"
    assert "已移除" in player["permission_label"]

    _login(client, user_id=2, username="player")
    denied = client.get(f"/api/rooms/{room['id']}")
    rejoined = client.post("/api/rooms/join", json={"room_code": room["room_code"]}).get_json()["data"]

    assert denied.status_code == 403
    assert len(rejoined["members"]) == 2
    player = next(member for member in rejoined["members"] if str(member["user_id"]) == "2")
    assert player["is_active"] is True
    assert player["status"] == "active"


def test_room_owner_cannot_bind_someone_elses_card_unless_global_admin(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client, user_id=1, username="owner")
    room = client.post("/api/rooms", json=_room_payload()).get_json()["data"]

    _login(client, user_id=2, username="player")
    client.post("/api/rooms/join", json={"room_code": room["room_code"]})

    _login(client, user_id=1, username="owner")
    rejected = client.put(
        f"/api/rooms/{room['id']}/members/2/character",
        json={"character_card": {"id": "owner-card", "name": "Owner Card", "playerId": "1"}},
    )

    _login(client, user_id=3, username="admin", role="ADMIN")
    accepted = client.put(
        f"/api/rooms/{room['id']}/members/2/character",
        json={"character_card": {"id": "admin-card", "name": "Admin Card", "playerId": "3"}},
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    player = next(member for member in accepted.get_json()["data"]["members"] if str(member["user_id"]) == "2")
    assert player["character_card"]["id"] == "admin-card"
