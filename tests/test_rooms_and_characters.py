import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trpg_server.app_factory import create_app


def _app(tmp_path):
    characters_dir = tmp_path / "characters"
    characters_dir.mkdir()
    occupations_dir = tmp_path / "occupations"
    occupations_dir.mkdir()
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
            "OCCUPATIONS_DIR": occupations_dir,
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


def test_bundled_character_skill_catalog_matches_documented_shape():
    project_root = Path(__file__).resolve().parents[1]
    catalog_path = project_root / "data" / "config" / "character_skills.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert catalog["version"] == 1
    skills = catalog["skills"]
    by_key = {skill["key"]: skill for skill in skills}
    assert by_key["creditRating"]["labelKey"] == "skills.creditRating"
    assert by_key["artCraft"]["repeatable"] == 3
    assert by_key["artCraft"]["specialties"][0]["key"] == "acting"
    assert by_key["languageOther"]["repeatable"] == 2
    assert by_key["computerUse"]["eraLimited"] is True
    assert catalog["locales"]["zh-CN"]["skills.artCraft"] == "技艺"
    assert catalog["locales"]["zh-CN"]["skillSpecialties.artCraft.writing"] == "写作"


def test_bundled_writer_occupation_uses_skill_keys_and_formula_terms():
    project_root = Path(__file__).resolve().parents[1]
    occupations_dir = project_root / "data" / "occupations" / "builtin"
    occupation_files = sorted(occupations_dir.glob("*.json"))

    assert [path.name for path in occupation_files] == ["writer.json"]
    writer = json.loads((occupations_dir / "writer.json").read_text(encoding="utf-8"))
    assert writer == {
        "id": "writer",
        "nameKey": "occupations.writer",
        "creditRating": {"min": 9, "max": 30},
        "occupationSkillPoints": {
            "formula": "EDU * 4",
            "terms": [{"attribute": "EDU", "multiplier": 4}],
        },
        "occupationSkills": [
            {"skillKey": "artCraft", "specialtyKey": "writing"},
            {"skillKey": "history"},
            {"skillKey": "libraryUse"},
            {"chooseOne": [{"skillKey": "naturalWorld"}, {"skillKey": "occult"}]},
            {"skillKey": "languageOther"},
            {"skillKey": "languageOwn"},
            {"skillKey": "psychology"},
            {"freeChoice": "personalOrEraSpecialty"},
        ],
    }


def test_character_catalog_api_lists_builtin_occupations(tmp_path):
    client = _app(tmp_path).test_client()
    occupations_dir = Path(client.application.config["OCCUPATIONS_DIR"]) / "builtin"
    occupations_dir.mkdir(parents=True)
    (occupations_dir / "writer.json").write_text(
        json.dumps(
            {
                "id": "writer",
                "nameKey": "occupations.writer",
                "creditRating": {"min": 9, "max": 30},
                "occupationSkillPoints": {
                    "formula": "EDU * 4",
                    "terms": [{"attribute": "EDU", "multiplier": 4}],
                },
                "occupationSkills": [{"skillKey": "history"}],
            }
        ),
        encoding="utf-8",
    )
    _login(client)

    response = client.get("/api/character-catalogs/occupations")

    assert response.status_code == 200
    assert response.get_json()["data"] == [
        {
            "id": "writer",
            "nameKey": "occupations.writer",
            "creditRating": {"min": 9, "max": 30},
            "occupationSkillPoints": {
                "formula": "EDU * 4",
                "terms": [{"attribute": "EDU", "multiplier": 4}],
            },
            "occupationSkills": [{"skillKey": "history"}],
        }
    ]


def test_character_editor_places_skill_controls_after_status_as_own_section():
    project_root = Path(__file__).resolve().parents[1]
    editor_html = (project_root / "frontend" / "src" / "index" / "fragments" / "04-editor-modals.html").read_text(
        encoding="utf-8"
    )
    status_index = editor_html.index("<span>人物状态</span><small>Character Status</small>")
    skill_index = editor_html.index("<span>技能</span><small>Skills</small>")
    background_index = editor_html.index("> 背景信息</h6>")

    assert 'id="characterSkillChecklist"' not in editor_html
    assert 'id="characterSkills"' not in editor_html
    assert 'id="autoAllocateOccupationSkills"' not in editor_html
    assert '<section class="character-form-section character-skill-editor-panel">' in editor_html
    assert status_index < skill_index < background_index
    assert '<span>技能</span><small>Skills</small>' in editor_html
    assert 'id="characterOccupationSkillPoints"' in editor_html
    assert 'id="characterPersonalInterestPoints"' in editor_html
    assert 'id="characterOccupationSkillLimit"' in editor_html
    assert 'id="characterOtherSkillLimit"' in editor_html


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


def test_user_actions_are_logged_in_natural_language_without_access_logs(tmp_path, monkeypatch):
    app = _app(tmp_path)
    scenarios_dir = tmp_path / "scenarios"
    scenario_covers_dir = tmp_path / "scenario_covers"
    scenarios_dir.mkdir()
    scenario_covers_dir.mkdir()

    import trpg_server.routes.scenarios as scenarios_routes

    monkeypatch.setattr(scenarios_routes, "SCENARIOS_DIR", scenarios_dir)
    monkeypatch.setattr(scenarios_routes, "SCENARIO_COVERS_DIR", scenario_covers_dir)

    client = app.test_client()
    _login(client)

    room_response = client.post(
        "/api/rooms",
        json={"name": "深夜车站", "scenario_id": 7, "scenario_title": "长生俑"},
    )
    character_response = client.put(
        "/api/characters/investigator-1",
        json={"id": "investigator-1", "name": "林见山", "playerId": "1"},
    )
    scenario_response = client.post(
        "/api/scenarios",
        json={"title": "雨夜来客", "description": "测试剧本"},
    )
    config_response = client.post(
        "/api/config/general",
        json={"character_rules": {"max_cards_per_user": 6}},
    )
    client.get("/api/rooms")

    assert room_response.status_code == 201
    assert character_response.status_code == 200
    assert scenario_response.status_code == 201
    assert config_response.status_code == 200

    log_files = sorted(Path(app.config["LOGS_DIR"]).glob("ai_trpg_*.log"))
    assert log_files
    messages = log_files[-1].read_text(encoding="utf-8").splitlines()
    assert any("用户 alice 创建了房间" in message and "深夜车站" in message for message in messages)
    assert any("用户 alice 保存了角色卡" in message and "林见山" in message for message in messages)
    assert any("用户 alice 创建了剧本" in message and "雨夜来客" in message for message in messages)
    assert any("用户 alice 更改了通用设置" in message for message in messages)
    assert all("GET /" not in message and "POST /" not in message for message in messages)
