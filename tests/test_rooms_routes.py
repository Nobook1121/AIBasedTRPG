import logging

from trpg_server.app_factory import create_app


PASSWORD = "StrongPass1"


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def _login_user(client, username="alice", role="USER"):
    manager = client.application.config["USER_MANAGER"]
    ok, message, user = manager.register(
        username,
        PASSWORD,
        f"{username.lower()}@example.com",
        terms_accepted=True,
    )
    assert ok, message
    if role != "USER":
        ok, message = manager.update_user_role(user["id"], role)
        assert ok, message

    response = client.post(
        "/api/auth/login",
        json={"identifier": username, "password": PASSWORD},
    )
    assert response.status_code == 200
    return response.get_json()["data"]


def _rooms_app(tmp_path):
    app = create_app(
        {
            "ROOMS_DIR": tmp_path / "rooms",
            "USER_DATABASE_FILE": tmp_path / "users.sqlite3",
            "USERS_FILE": tmp_path / "users.json",
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
        }
    )
    return app, app.config["ROOMS_DIR"]


def _create_room(client, name="Run One", scenario_id=12):
    response = client.post(
        "/api/rooms",
        json={
            "name": name,
            "scenario_id": scenario_id,
            "scenario_title": "Scenario",
            "character_card": _character_card("Investigator"),
        },
    )
    assert response.status_code == 201
    return response.get_json()["data"]


def _character_card(name="Investigator"):
    return {
        "id": f"card-{name.lower()}",
        "name": name,
        "occupationId": "detective",
        "attributes": {"STR": 50, "CON": 60, "SIZ": 70, "DEX": 55, "INT": 80, "POW": 65, "AGE": 42},
        "maxHp": 13,
        "currentHp": 13,
        "maxSan": 43,
        "currentSan": 43,
        "mov": 6,
        "skills": [],
        "equipment": [],
        "background": {"raceType": "human"},
        "injuryRecords": [{"damage": 99, "note": "must not be copied"}],
        "sanityRecords": [{"loss": 99, "note": "must not be copied"}],
    }


def test_user_creates_room_with_unique_code_and_initial_membership(tmp_path):
    app, rooms_dir = _rooms_app(tmp_path)
    client = app.test_client()
    user = _login_user(client)

    room = _create_room(client)

    assert room["name"] == "Run One"
    assert len(room["room_code"]) >= 6
    assert room["creator_id"] == user["user_id"]
    assert room["members"][0]["user_id"] == user["user_id"]
    assert room["members"][0]["character_card"]["name"] == "Investigator"
    assert room["members"][0]["character_state"]["current_hp"] == 13
    assert room["members"][0]["character_state"]["injury_records"] == []
    assert "injuryRecords" not in room["members"][0]["character_card"]
    assert (rooms_dir / room["id"] / "info.json").exists()
    assert (rooms_dir / room["id"] / "messages.json").exists()


def test_normal_user_must_bind_character_when_creating_room(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    _login_user(client)

    response = client.post(
        "/api/rooms",
        json={"name": "No Card", "scenario_id": 12, "scenario_title": "Scenario"},
    )

    assert response.status_code == 400
    assert "Character card is required" in response.get_json()["error"]


def test_room_names_must_be_unique(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    _login_user(client)
    _create_room(client, name="Same Name")

    response = client.post(
        "/api/rooms",
        json={
            "name": "Same Name",
            "scenario_id": 12,
            "scenario_title": "Scenario",
            "character_card": _character_card("Second"),
        },
    )

    assert response.status_code == 409
    assert "Room name already exists" in response.get_json()["error"]


def test_user_room_creation_is_limited_to_three_rooms(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    _login_user(client)

    for index in range(3):
        _create_room(client, name=f"Run {index}")

    response = client.post(
        "/api/rooms",
        json={"name": "Run 4", "scenario_id": 12, "scenario_title": "Scenario"},
    )

    assert response.status_code == 403
    assert "Room creation limit reached" in response.get_json()["error"]


def test_admin_can_create_unlimited_rooms_and_watch_any_room(tmp_path):
    app, _ = _rooms_app(tmp_path)
    owner_client = app.test_client()
    admin_client = app.test_client()
    _login_user(owner_client)
    _login_user(admin_client, username="ADMIN", role="ADMIN")

    room = _create_room(owner_client)
    for index in range(4):
        response = admin_client.post(
            "/api/rooms",
            json={"name": f"Admin {index}", "scenario_id": 12, "scenario_title": "Scenario"},
        )
        assert response.status_code == 201

    watch_response = admin_client.get(f"/api/rooms/{room['id']}")

    assert watch_response.status_code == 200
    assert watch_response.get_json()["data"]["id"] == room["id"]


def test_user_joins_room_by_code_and_can_load_messages(tmp_path):
    app, _ = _rooms_app(tmp_path)
    owner_client = app.test_client()
    player_client = app.test_client()
    _login_user(owner_client)
    player = _login_user(player_client, username="bob")
    room = _create_room(owner_client)

    missing_card_response = player_client.post("/api/rooms/join", json={"room_code": room["room_code"]})
    join_response = player_client.post(
        "/api/rooms/join",
        json={"room_code": room["room_code"], "character_card": _character_card("Bob Investigator")},
    )
    detail_response = player_client.get(f"/api/rooms/{room['id']}")

    assert missing_card_response.status_code == 400
    assert join_response.status_code == 200
    assert detail_response.status_code == 200
    members = detail_response.get_json()["data"]["members"]
    assert any(
        member["user_id"] == player["user_id"]
        and member["character_card"]["name"] == "Bob Investigator"
        for member in members
    )


def test_room_character_records_are_room_scoped_and_admin_delete_only(tmp_path):
    app, _ = _rooms_app(tmp_path)
    owner_client = app.test_client()
    admin_client = app.test_client()
    _login_user(owner_client, username="owner")
    admin = _login_user(admin_client, username="admin", role="ADMIN")
    room = _create_room(owner_client)

    record_response = owner_client.post(
        f"/api/rooms/{room['id']}/character-records",
        json={"type": "damage", "username": "owner", "value": 3, "reason": "knife"},
    )
    room_response = owner_client.get(f"/api/rooms/{room['id']}")
    record_id = record_response.get_json()["data"]["record"]["id"]
    normal_delete = owner_client.delete(f"/api/rooms/{room['id']}/character-records/{record_id}")
    admin_delete = admin_client.delete(f"/api/rooms/{room['id']}/character-records/{record_id}")
    after_delete = admin_client.get(f"/api/rooms/{room['id']}")

    assert admin["role"] == "ADMIN"
    assert record_response.status_code == 201
    owner_member = next(member for member in room_response.get_json()["data"]["members"] if member["username"] == "owner")
    assert owner_member["character_state"]["current_hp"] == 10
    assert owner_member["character_state"]["injury_records"][0]["reason"] == "knife"
    assert normal_delete.status_code == 403
    assert admin_delete.status_code == 200
    owner_member_after = next(member for member in after_delete.get_json()["data"]["members"] if member["username"] == "owner")
    assert owner_member_after["character_state"]["injury_records"] == []


def test_room_character_record_can_target_room_by_unique_name(tmp_path):
    app, _ = _rooms_app(tmp_path)
    owner_client = app.test_client()
    _login_user(owner_client, username="owner")
    room = _create_room(owner_client, name="Named Room")

    response = owner_client.post(
        "/api/rooms/by-name/Named%20Room/character-records",
        json={"type": "san", "username": "owner", "value": 2, "reason": "vision"},
    )
    detail = owner_client.get(f"/api/rooms/{room['id']}")

    assert response.status_code == 201
    owner_member = next(member for member in detail.get_json()["data"]["members"] if member["username"] == "owner")
    assert owner_member["character_state"]["current_san"] == 41
    assert owner_member["character_state"]["sanity_records"][0]["reason"] == "vision"


def test_room_message_persists_sender_identity_and_avatar(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    user = _login_user(client)
    room = _create_room(client)

    response = client.post(
        f"/api/rooms/{room['id']}/messages",
        json={"type": "player", "content": "hello"},
    )
    messages_response = client.get(f"/api/rooms/{room['id']}/messages")

    assert response.status_code == 201
    message = response.get_json()["data"]
    assert message["sender_id"] == user["user_id"]
    assert message["sender_name"] == "alice"
    assert message["avatar"]
    assert messages_response.get_json()["data"][0]["content"] == "hello"


def test_room_message_log_includes_content_and_command_result(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    _login_user(client)
    room = _create_room(client)
    logger = logging.getLogger("trpg_server.routes.rooms")
    handler = ListHandler()
    logger.addHandler(handler)

    try:
        client.post(f"/api/rooms/{room['id']}/messages", json={"type": "player", "content": "/dice 1d20"})
        client.post(f"/api/rooms/{room['id']}/messages", json={"type": "dice", "content": "检定结果：18"})
    finally:
        logger.removeHandler(handler)

    assert any("content=/dice 1d20" in message for message in handler.messages)
    assert any("content=检定结果：18" in message for message in handler.messages)


def test_room_save_node_restore_replaces_current_messages(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    _login_user(client)
    room = _create_room(client)
    client.post(f"/api/rooms/{room['id']}/messages", json={"type": "player", "content": "before"})
    node_response = client.post(f"/api/rooms/{room['id']}/nodes")
    client.post(f"/api/rooms/{room['id']}/messages", json={"type": "player", "content": "after"})

    restore_response = client.post(
        f"/api/rooms/{room['id']}/nodes/{node_response.get_json()['data']['filename']}/restore"
    )
    messages_response = client.get(f"/api/rooms/{room['id']}/messages")

    assert restore_response.status_code == 200
    assert [message["content"] for message in messages_response.get_json()["data"]] == ["before"]


def test_room_autosave_round_trip_uses_current_messages(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    _login_user(client)
    room = _create_room(client)
    client.post(f"/api/rooms/{room['id']}/messages", json={"type": "player", "content": "saved"})

    save_response = client.post(f"/api/rooms/{room['id']}/autosave")
    load_response = client.get(f"/api/rooms/{room['id']}/autosave")

    assert save_response.status_code == 200
    assert load_response.get_json()["data"]["messages"][0]["content"] == "saved"


def test_invalidated_session_cannot_use_room_routes(tmp_path):
    app, _ = _rooms_app(tmp_path)
    client = app.test_client()
    _login_user(client)
    with client.session_transaction() as session:
        session["session_token"] = "old-token"

    response = client.get("/api/rooms")

    assert response.status_code == 401
