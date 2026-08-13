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
    weapons_dir = tmp_path / "weapons"
    weapons_dir.mkdir()
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
            "WEAPONS_DIR": weapons_dir,
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


def test_room_check_tool_api_uses_bound_character_card(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client)
    room = client.post("/api/rooms", json=_room_payload()).get_json()["data"]
    user_id = str(room["members"][0]["user_id"])
    bound = client.put(
        f"/api/rooms/{room['id']}/members/{user_id}/character",
        json={
            "character_card": {
                "id": "owned",
                "name": "Owned",
                "playerId": "1",
                "attributes": {"DEX": 60},
                "maxHp": 10,
                "maxSan": 50,
                "skills": [{"name": "侦察", "value": 70}],
            }
        },
    )

    response = client.post(
        f"/api/rooms/{room['id']}/tools/check",
        json={"player_name": "alice", "name": "侦察", "difficulty": "困难", "adjustment": "+5"},
    )

    assert bound.status_code == 200
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["player_name"] == "alice"
    assert data["base_target"] == 70
    assert data["threshold"] == 40
    assert data["roll"] >= 1
    assert data["roll"] <= 100
    assert "summary" in data


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


def test_character_save_persists_test_character_json_shape_and_returns_runtime_card(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client)

    response = client.put(
        "/api/characters/owned",
        json={
            "id": "owned",
            "name": "Runtime Investigator",
            "playerId": "1",
            "occupationName": "Writer",
            "age": 34,
            "gender": "male",
            "residence": "Arkham",
            "birthplace": "Boston",
            "attributes": {
                "STR": 55,
                "DEX": 40,
                "CON": 70,
                "APP": 65,
                "POW": 65,
                "SIZ": 55,
                "EDU": 75,
                "INT": 55,
                "LUC": 40,
                "AGE": 34,
            },
            "currentHp": 7,
            "maxHp": 12,
            "currentSan": 41,
            "initialSan": 65,
            "maxSan": 99,
            "currentMp": 8,
            "maxMp": 13,
            "damageBonus": "0",
            "build": 0,
            "mov": 7,
            "armor": 5,
            "status": {
                "majorWound": True,
                "unconscious": False,
                "dead": False,
                "temporaryInsanity": True,
                "permanentInsanity": False,
                "indefiniteInsanity": True,
            },
            "skills": [
                {
                    "id": "firstAid",
                    "skillKey": "firstAid",
                    "name": "急救",
                    "base": 30,
                    "value": 45,
                    "category": "医疗",
                    "checked": True,
                    "occupation": True,
                    "occupationPoints": 10,
                    "interestPoints": 5,
                    "growthPoints": 0,
                }
            ],
            "weapons": [
                {
                    "name": "徒手格斗",
                    "skill": "格斗(斗殴)",
                    "skillKey": "fighting",
                    "specialtyKey": "brawl",
                    "damage": "1D3+DB",
                    "range": "接触",
                    "impale": False,
                    "attacks": "1",
                    "ammo": "N/A",
                    "malfunction": "N/A",
                }
            ],
            "equipment": [{"name": "手电筒", "quantity": 1, "weight": 0, "notes": "旧"}],
            "assets": {"cash": 10, "spendingLevel": 20, "assetsText": "房产"},
            "background": {
                "appearance": "appearance",
                "ideology": "belief",
                "significantPeople": "person",
                "meaningfulLocations": "place",
                "treasuredPossessions": "item",
                "traits": "trait",
                "injuriesScars": "scar",
                "phobiasManias": "mad",
                "story": "intro",
                "arcaneTomes": "myth item",
                "spells": "spells",
                "encounters": "touch",
            },
            "relationships": [{"name": "role", "description": "relation", "player": "player"}],
            "experiencedScenarios": [{"name": "scenario", "experience": "experience"}],
        },
    )

    assert response.status_code == 200
    saved_path = Path(client.application.config["CHARACTERS_DIR"]) / "owned.json"
    saved = json.loads(saved_path.read_text(encoding="utf-8"))

    assert saved["id"] == "owned"
    assert saved["playerId"] == "1"
    assert saved["job"] == "Writer"
    assert saved["location"] == "Arkham"
    assert saved["hometown"] == "Boston"
    assert saved["attributes"]["str"] == 55
    assert saved["deriveAttributes"]["hp"] == {"current": "7", "max": "12"}
    assert saved["deriveAttributes"]["sanity"] == {"current": "41", "start": "65", "max": "99"}
    assert saved["battleAttributes"]["armor"] == "5"
    assert saved["characterStatus"]["bodyStates"]["重伤"] is True
    assert saved["characterStatus"]["mentalStates"]["临时疯狂"] is True
    assert saved["skillGroups"]["medical"][0]["name"] == "急救"
    assert saved["skillGroups"]["medical"][0]["job"] == 10
    assert saved["weapons"][0]["round"] == "1"
    assert saved["assets"]["items"] == "手电筒 x1：旧"
    assert saved["assets"]["magicItems"] == "myth item"
    assert json.loads(saved["friends"]) == [{"character": "role", "relationship": "relation", "player": "player"}]
    assert json.loads(saved["experiencedModules"]) == [{"name": "scenario", "experience": "experience"}]
    assert "maxHp" not in saved
    assert "skills" not in saved

    listed = client.get("/api/characters").get_json()["data"]
    runtime = next(card for card in listed if card["id"] == "owned")
    assert runtime["maxHp"] == 12
    assert runtime["currentHp"] == 7
    assert runtime["maxSan"] == 99
    assert runtime["currentSan"] == 41
    assert runtime["background"]["arcaneTomes"] == "myth item"
    assert runtime["relationships"] == [{"name": "role", "description": "relation", "player": "player"}]


def test_character_api_reads_test_character_json_shape_from_disk(tmp_path):
    client = _app(tmp_path).test_client()
    characters_dir = Path(client.application.config["CHARACTERS_DIR"])
    (characters_dir / "external-card.json").write_text(
        json.dumps(
            {
                "name": "Imported Investigator",
                "playerId": "1",
                "playerName": "alice",
                "time": "1920s",
                "job": "Doctor",
                "age": "29",
                "gender": "female",
                "location": "London",
                "hometown": "York",
                "attributes": {
                    "str": 40,
                    "dex": 50,
                    "con": 60,
                    "app": 70,
                    "pow": 80,
                    "siz": 45,
                    "edu": 65,
                    "int": 75,
                    "luc": 35,
                },
                "deriveAttributes": {
                    "sanity": {"current": "70", "start": "80", "max": "99"},
                    "hp": {"current": "9", "max": "10"},
                    "mp": {"current": "11", "max": "16"},
                },
                "battleAttributes": {"db": "-1", "build": "-1", "mov": "8", "armor": "2"},
                "characterStatus": {
                    "bodyStates": {"重伤": False, "昏迷": True, "死亡": False},
                    "mentalStates": {"不定期疯狂": False, "永久疯狂": False, "临时疯狂": True},
                },
                "weapons": [{"name": "手枪", "skill": "射击(手枪)", "damage": "1D10", "range": "15", "round": "1"}],
                "stories": {
                    "app": "appearance",
                    "belief": "belief",
                    "IPerson": "person",
                    "IPlace": "place",
                    "IItem": "item",
                    "trait": "trait",
                    "scar": "scar",
                    "mad": "mad",
                    "desc": "intro",
                },
                "assets": {
                    "cash": "15",
                    "consumption": "25",
                    "assets": "assets",
                    "items": "rope",
                    "magicItems": "book",
                    "magics": "spell",
                    "touches": "encounter",
                },
                "friends": json.dumps([{"character": "npc", "relationship": "ally", "player": "bob"}]),
                "experiencedModules": json.dumps([{"name": "module", "experience": "survived"}]),
                "skillGroups": {
                    "medical": [
                        {
                            "id": "medicine",
                            "skillKey": "medicine",
                            "name": "医学",
                            "base": 1,
                            "job": 20,
                            "interest": 5,
                            "growth": 0,
                            "isProfessional": True,
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _login(client)

    response = client.get("/api/characters")

    assert response.status_code == 200
    runtime = next(card for card in response.get_json()["data"] if card["id"] == "external-card")
    assert runtime["name"] == "Imported Investigator"
    assert runtime["occupationName"] == "Doctor"
    assert runtime["residence"] == "London"
    assert runtime["birthplace"] == "York"
    assert runtime["attributes"]["STR"] == 40
    assert runtime["attributes"]["AGE"] == 29
    assert runtime["currentHp"] == 9
    assert runtime["maxHp"] == 10
    assert runtime["currentMp"] == 11
    assert runtime["maxMp"] == 16
    assert runtime["status"]["unconscious"] is True
    assert runtime["status"]["temporaryInsanity"] is True
    assert runtime["background"]["arcaneTomes"] == "book"
    assert runtime["relationships"][0]["name"] == "npc"
    assert runtime["experiencedScenarios"][0]["name"] == "module"
    assert runtime["skills"][0]["id"] == "medicine"


def test_saving_legacy_character_file_migrates_it_to_test_character_json_shape(tmp_path):
    client = _app(tmp_path).test_client()
    characters_dir = Path(client.application.config["CHARACTERS_DIR"])
    (characters_dir / "legacy.json").write_text(
        json.dumps({"id": "legacy", "name": "Legacy", "playerId": "1", "maxHp": 9, "currentHp": 4}),
        encoding="utf-8",
    )
    _login(client)

    response = client.put("/api/characters/legacy", json={"id": "legacy", "name": "Migrated", "playerId": "1"})

    assert response.status_code == 200
    saved = json.loads((characters_dir / "legacy.json").read_text(encoding="utf-8"))
    assert saved["name"] == "Migrated"
    assert "deriveAttributes" in saved
    assert "battleAttributes" in saved
    assert "maxHp" not in saved


def test_saving_character_updates_bound_room_member_snapshot(tmp_path):
    client = _app(tmp_path).test_client()
    _login(client)
    room = client.post("/api/rooms", json=_room_payload()).get_json()["data"]
    user_id = str(room["members"][0]["user_id"])

    card = {"id": "owned", "name": "Old Name", "playerId": "1", "maxHp": 10, "maxSan": 50}
    bound = client.put(f"/api/rooms/{room['id']}/members/{user_id}/character", json={"character_card": card})
    saved = client.put("/api/characters/owned", json={**card, "name": "New Name", "maxHp": 12, "maxSan": 55})

    assert bound.status_code == 200
    assert saved.status_code == 200
    refreshed = client.get(f"/api/rooms/{room['id']}").get_json()["data"]
    member = next(member for member in refreshed["members"] if str(member["user_id"]) == user_id)
    assert member["character_card"]["name"] == "New Name"
    assert member["character_card"]["maxHp"] == 12
    assert member["character_card"]["maxSan"] == 55
    assert member["character_state"]["max_hp"] == 12
    assert member["character_state"]["max_san"] == 55


def test_bundled_character_skill_catalog_matches_documented_shape():
    project_root = Path(__file__).resolve().parents[1]
    catalog_path = project_root / "data" / "config" / "character_skills.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert catalog["version"] == 1
    skills = catalog["skills"]
    by_key = {skill["key"]: skill for skill in skills}
    categories = {skill["category"] for skill in skills}
    assert categories == {"特殊", "探索", "社交", "战斗", "医疗", "运动", "知识", "技术", "操纵", "其他"}
    assert by_key["creditRating"]["labelKey"] == "skills.creditRating"
    assert by_key["creditRating"]["category"] == "特殊"
    assert by_key["creditRating"]["base"] == 0
    assert by_key["psychology"]["category"] == "社交"
    assert by_key["psychology"]["base"] == 10
    assert by_key["firstAid"]["category"] == "医疗"
    assert by_key["medicine"]["category"] == "医疗"
    assert by_key["psychoanalysis"]["category"] == "医疗"
    assert by_key["hypnosis"]["category"] == "医疗"
    assert by_key["firstAid"]["base"] == 30
    assert by_key["artCraft"]["repeatable"] == 3
    assert by_key["artCraft"]["category"] == "技术"
    assert by_key["artCraft"]["base"] == 5
    assert by_key["artCraft"]["specialties"][0]["key"] == "acting"
    assert by_key["languageOther"]["repeatable"] == 2
    assert by_key["languageOther"]["category"] == "社交"
    assert by_key["languageOther"]["base"] == 1
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
        "skillBases": {
            "artCraft": 5,
            "history": 5,
            "libraryUse": 20,
            "naturalWorld": 10,
            "occult": 5,
            "languageOther": 1,
            "languageOwn": 0,
            "psychology": 10,
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


def test_character_catalog_api_returns_skill_catalog(tmp_path):
    client = _app(tmp_path).test_client()
    config_dir = Path(client.application.config["CONFIG_DIR"])
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "character_skills.json").write_text(
        json.dumps(
            {
                "version": 1,
                "defaultLocale": "zh-CN",
                "skills": [
                    {
                        "key": "history",
                        "labelKey": "skills.history",
                        "category": "知识",
                        "base": 5,
                        "repeatable": 1,
                        "specialties": [],
                    }
                ],
                "locales": {"zh-CN": {"skills.history": "历史"}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _login(client)

    response = client.get("/api/character-catalogs/skills")

    assert response.status_code == 200
    assert response.get_json()["data"]["skills"][0]["key"] == "history"
    assert response.get_json()["data"]["skills"][0]["category"] == "知识"


def test_bundled_fist_weapon_uses_builtin_weapon_shape():
    project_root = Path(__file__).resolve().parents[1]
    weapons_dir = project_root / "data" / "weapons" / "builtin"
    weapon_files = sorted(weapons_dir.glob("*.json"))

    assert [path.name for path in weapon_files] == ["fist.json"]
    fist = json.loads((weapons_dir / "fist.json").read_text(encoding="utf-8"))
    assert fist == {
        "id": "fist",
        "name": "徒手格斗",
        "skill": {"skillKey": "fighting", "specialtyKey": "brawl", "label": "格斗(斗殴)"},
        "damage": "1D3+DB",
        "attacks": "1",
        "impale": False,
        "range": "接触",
        "ammo": "N/A",
        "malfunction": "N/A",
        "eras": ["1920s", "现代"],
        "price": "N/A",
    }


def test_character_catalog_api_lists_builtin_weapons(tmp_path):
    client = _app(tmp_path).test_client()
    weapons_dir = Path(client.application.config["WEAPONS_DIR"]) / "builtin"
    weapons_dir.mkdir(parents=True)
    (weapons_dir / "fist.json").write_text(
        json.dumps(
            {
                "id": "fist",
                "name": "徒手格斗",
                "skill": {"skillKey": "fighting", "specialtyKey": "brawl", "label": "格斗(斗殴)"},
                "damage": "1D3+DB",
                "attacks": "1",
                "impale": False,
                "range": "接触",
                "ammo": "N/A",
                "malfunction": "N/A",
                "eras": ["1920s", "现代"],
                "price": "N/A",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _login(client)

    response = client.get("/api/character-catalogs/weapons")

    assert response.status_code == 200
    assert response.get_json()["data"] == [
        {
            "id": "fist",
            "name": "徒手格斗",
            "skill": {"skillKey": "fighting", "specialtyKey": "brawl", "label": "格斗(斗殴)"},
            "damage": "1D3+DB",
            "attacks": "1",
            "impale": False,
            "range": "接触",
            "ammo": "N/A",
            "malfunction": "N/A",
            "eras": ["1920s", "现代"],
            "price": "N/A",
        }
    ]


def test_character_editor_places_skill_controls_after_status_as_own_section():
    project_root = Path(__file__).resolve().parents[1]
    editor_html = (project_root / "frontend" / "src" / "index" / "fragments" / "04-editor-modals.html").read_text(
        encoding="utf-8"
    )
    status_index = editor_html.index("<span>人物状态</span><small>Character Status</small>")
    skill_index = editor_html.index("<span>技能</span><small>Skills</small>")
    mythos_index = editor_html.index("<small>Cthulu Mythos</small>")

    assert 'id="characterSkillChecklist"' not in editor_html
    assert 'id="characterSkills"' not in editor_html
    assert 'id="autoAllocateOccupationSkills"' not in editor_html
    assert '<section class="character-form-section character-skill-editor-panel">' in editor_html
    assert status_index < skill_index < mythos_index
    assert '<span>技能</span><small>Skills</small>' in editor_html
    assert 'id="characterOccupationSkillPoints"' in editor_html
    assert 'id="characterPersonalInterestPoints"' in editor_html
    assert 'id="characterOccupationSkillLimit"' in editor_html
    assert 'id="characterOtherSkillLimit"' in editor_html
    assert 'id="characterSkillCategoryFilters"' in editor_html
    for category in ["全部技能", "特殊", "探索", "社交", "战斗", "医疗", "运动", "知识", "技术", "操纵", "其他"]:
        assert f'data-skill-category="{category}"' in editor_html
    assert 'id="characterSkillTableBody"' in editor_html
    for heading in ["专职", "技能名称", "基础%", "职业%", "兴趣%", "成长%", "成功率%", "困难50%", "噩梦20%"]:
        assert f"<th>{heading}</th>" in editor_html


def test_character_editor_places_weapons_then_combat_as_independent_sections():
    project_root = Path(__file__).resolve().parents[1]
    editor_html = (project_root / "frontend" / "src" / "index" / "fragments" / "04-editor-modals.html").read_text(
        encoding="utf-8"
    )
    skill_index = editor_html.index("<span>技能</span><small>Skills</small>")
    weapons_index = editor_html.index("<span>武器</span><small>Weapons</small>")
    combat_index = editor_html.index("<span>战斗</span><small>Combat</small>")
    mythos_index = editor_html.index("<small>Cthulu Mythos</small>")

    assert '<div class="character-combat-layout">' not in editor_html
    assert '<section class="character-form-section character-weapon-editor-panel">' in editor_html
    assert '<section class="character-form-section character-combat-editor-panel">' in editor_html
    assert skill_index < weapons_index < combat_index < mythos_index
    assert 'id="characterWeaponTableBody"' in editor_html
    assert 'id="characterWeaponPickerModal"' in editor_html
    assert 'id="characterWeaponCatalogList"' in editor_html
    assert 'id="createCustomWeapon"' in editor_html
    assert 'id="removeCurrentWeapon"' in editor_html
    assert 'id="characterWeapons"' not in editor_html
    for heading in ["武器名称", "使用技能", "成功率", "伤害", "射程", "贯穿", "次数", "装弹量", "故障率"]:
        assert f"<th>{heading}</th>" in editor_html
    for field_id in ["characterDamageBonus", "characterBuild", "characterArmor", "characterMov"]:
        assert f'id="{field_id}"' in editor_html


def test_character_editor_places_possessions_and_assets_after_combat_as_independent_sections():
    project_root = Path(__file__).resolve().parents[1]
    editor_html = (project_root / "frontend" / "src" / "index" / "fragments" / "04-editor-modals.html").read_text(
        encoding="utf-8"
    )

    combat_index = editor_html.index("<small>Combat</small>")
    possessions_index = editor_html.index("<small>Possessions</small>")
    assets_index = editor_html.index("<small>Cash & Assets</small>")
    mythos_index = editor_html.index("<small>Cthulu Mythos</small>")

    assert '<section class="character-form-section character-possessions-editor-panel">' in editor_html
    assert '<section class="character-form-section character-assets-editor-panel">' in editor_html
    assert combat_index < possessions_index < assets_index < mythos_index
    assert '<span>物品与装备</span><small>Possessions</small>' in editor_html
    assert '<span>资产</span><small>Cash & Assets</small>' in editor_html
    assert '<label class="form-label" for="characterEquipment">' not in editor_html
    assert 'id="characterEquipment"' in editor_html
    assert 'id="characterCreditRating"' in editor_html
    assert 'id="characterCreditRating" min="0" max="99" readonly' in editor_html
    assert 'id="characterCash"' in editor_html
    assert 'id="characterSpendingLevel"' in editor_html
    assert 'id="characterAssets"' in editor_html
    assert "快速录入" not in editor_html


def test_character_editor_adds_mythos_story_companions_and_scenarios_sections_after_assets():
    project_root = Path(__file__).resolve().parents[1]
    editor_html = (project_root / "frontend" / "src" / "index" / "fragments" / "04-editor-modals.html").read_text(
        encoding="utf-8"
    )

    assets_index = editor_html.index("<small>Cash & Assets</small>")
    mythos_index = editor_html.index("<small>Cthulu Mythos</small>")
    story_index = editor_html.index("<small>Story</small>")
    companions_index = editor_html.index("<small>Companions</small>")
    scenarios_index = editor_html.index("<small>Experienced Scenarios</small>")

    assert assets_index < mythos_index < story_index < companions_index < scenarios_index
    assert '<section class="character-form-section character-mythos-editor-panel">' in editor_html
    assert '<section class="character-form-section character-story-editor-panel">' in editor_html
    assert '<section class="character-form-section character-companions-editor-panel">' in editor_html
    assert '<section class="character-form-section character-scenarios-editor-panel">' in editor_html
    assert '<label class="form-label" for="characterEquipment">\u7269\u54c1\u4e0e\u88c5\u5907</label>' not in editor_html
    assert 'placeholder="\u5728\u6b64\u8f93\u5165\u7269\u54c1\u4e0e\u88c5\u5907\u4fe1\u606f..."' in editor_html

    for field_id, placeholder in {
        "characterArcaneTomes": "\u9b54\u6cd5\u7269\u54c1\u4e0e\u5178\u7c4d",
        "characterSpells": "\u6cd5\u672f",
        "characterEncounters": "\u7b2c\u4e09\u7c7b\u63a5\u89e6",
        "characterBio": "\u4e2a\u4eba\u4ecb\u7ecd",
        "appearance": "\u5f62\u8c61\u63cf\u8ff0",
        "characterIdeology": "\u601d\u60f3\u4e0e\u4fe1\u5ff5",
        "characterSignificantPeople": "\u91cd\u8981\u4e4b\u4eba",
        "characterMeaningfulLocations": "\u610f\u4e49\u975e\u51e1\u4e4b\u5730",
        "characterTreasuredPossessions": "\u5b9d\u8d35\u4e4b\u7269",
        "traits": "\u7279\u8d28",
        "characterInjuriesScars": "\u4f24\u53e3\u4e0e\u75a4\u75d5",
        "characterPhobiasManias": "\u7cbe\u795e\u75c7\u72b6",
        "characterCompanionRole": "\u89d2\u8272",
        "characterCompanionRelationship": "\u5173\u7cfb",
        "characterCompanionPlayer": "\u73a9\u5bb6",
        "characterScenarioName": "\u6a21\u7ec4",
        "characterScenarioExperience": "\u7ecf\u5386",
    }.items():
        assert f'id="{field_id}"' in editor_html
        assert f'placeholder="{placeholder}"' in editor_html


def test_character_editor_structured_background_relationships_and_scenarios_are_persisted():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    assert "interface COC7ExperiencedScenario" in source
    assert "spells: string;" in source
    assert "player: string;" in source
    assert "experiencedScenarios: COC7ExperiencedScenario[]" in source
    assert 'setInputValue("characterArcaneTomes", target.background.arcaneTomes)' in source
    assert 'setInputValue("characterSpells", target.background.spells)' in source
    assert 'setInputValue("characterEncounters", target.background.encounters)' in source
    assert 'setInputValue("characterIdeology", target.background.ideology)' in source
    assert 'setInputValue("characterSignificantPeople", target.background.significantPeople)' in source
    assert 'setInputValue("characterMeaningfulLocations", target.background.meaningfulLocations)' in source
    assert 'setInputValue("characterTreasuredPossessions", target.background.treasuredPossessions)' in source
    assert 'setInputValue("characterInjuriesScars", target.background.injuriesScars)' in source
    assert 'setInputValue("characterPhobiasManias", target.background.phobiasManias)' in source
    assert "hydrateRelationshipRows(target.relationships)" in source
    assert "hydrateExperiencedScenarioRows(target.experiencedScenarios)" in source
    assert 'arcaneTomes: getInputValue("characterArcaneTomes")' in source
    assert 'spells: getInputValue("characterSpells")' in source
    assert 'encounters: getInputValue("characterEncounters")' in source
    assert 'ideology: getInputValue("characterIdeology")' in source
    assert 'significantPeople: getInputValue("characterSignificantPeople")' in source
    assert 'meaningfulLocations: getInputValue("characterMeaningfulLocations")' in source
    assert 'treasuredPossessions: getInputValue("characterTreasuredPossessions")' in source
    assert 'injuriesScars: getInputValue("characterInjuriesScars")' in source
    assert 'phobiasManias: getInputValue("characterPhobiasManias")' in source
    assert "relationships: readRelationshipRows()" in source
    assert "experiencedScenarios: readExperiencedScenarioRows()" in source


def test_character_detail_matches_editor_sections_without_extra_summary_content():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")
    detail_source = source[source.index("function renderCharacterDetail") : source.index("function deleteCard")]

    assert "character-detail-dashboard" in source
    assert "character-detail-band" in source
    assert "renderCharacterVitals" in source
    assert "renderCharacterBackgroundSections" in source
    assert "renderCharacterBasicInfo" in source
    assert "renderCharacterSkillSection" in source
    assert "renderCharacterWeaponsSection" in source
    assert "renderCharacterPossessionsSection" in source
    assert "renderCharacterAssetsSection" in source
    assert "renderTopSkills" not in source
    assert "renderCombatAndAssets" not in source

    ordered_sections = [
        "renderCharacterBasicInfo(card)",
        "属性",
        "renderCharacterVitals(card)",
        "renderCharacterStatusSection(card)",
        "renderCharacterSkillSection(card)",
        "renderCharacterWeaponsSection(card)",
        "renderCharacterCombatSection(card)",
        "renderCharacterPossessionsSection(card)",
        "renderCharacterAssetsSection(card)",
        "renderCharacterBackgroundSections(card)",
    ]
    positions = [detail_source.index(section) for section in ordered_sections]
    assert positions == sorted(positions)
    for extra_text in ["核心状态", "技能重点", "战斗与资产", "总重量"]:
        assert extra_text not in detail_source


def test_character_weapon_name_column_wraps_between_chinese_words():
    project_root = Path(__file__).resolve().parents[1]
    character_css = (project_root / "frontend" / "src" / "styles" / "02-scenario-character.css").read_text(
        encoding="utf-8"
    )
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    assert ".character-weapon-name-button" in character_css
    assert "word-break: keep-all;" in character_css
    assert "formatWeaponNameForDisplay" in source
    assert 'replace(/\\s+/g, "<wbr>")' in source


def test_character_editor_rewrites_assets_fields_and_syncs_credit_rating_from_skills():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    assert "function syncEditorCreditRating" in source
    assert "function readEditorCreditRating" in source
    assert "function readEditorAssets" in source
    assert 'setInputValue("characterCash", target.assets.cash)' in source
    assert 'setInputValue("characterSpendingLevel", target.assets.spendingLevel)' in source
    assert 'setInputValue("characterAssets", target.assets.assetsText)' in source
    assert "creditRating: readEditorCreditRating()" in source
    assert "assets: readEditorAssets()" in source
    assert "parseAssets(" not in source
    assert "formatAssets(" not in source


def test_character_rule_settings_include_admin_weapon_slot_count():
    project_root = Path(__file__).resolve().parents[1]
    settings_html = (
        project_root / "frontend" / "src" / "index" / "fragments" / "03-room-tools-auth-settings.html"
    ).read_text(encoding="utf-8")
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")
    general_config = (project_root / "data" / "config" / "general.toml").read_text(encoding="utf-8")

    assert 'id="weaponSlotCount"' in settings_html
    assert "默认武器栏位数量" in settings_html
    assert "weaponSlotCount: 5" in source
    assert "weapon_slot_count" in source
    assert "weapon_slot_count = 5" in general_config


def test_character_editor_weapon_script_reads_structured_rows_and_refreshes_success_rates():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    assert "interface WeaponCatalogPayload" in source
    assert '"/api/character-catalogs/weapons"' in source
    assert "function renderWeaponTable" in source
    assert "function readWeaponRows" in source
    assert "function refreshWeaponSuccessRates" in source
    assert "data-weapon-success" in source
    assert "findSkillSuccessByWeaponSkill" in source
    assert "weaponPickerModal" in source
    assert "characterArmor" in source
    assert "getWeaponSlotCount()" in source
    assert "ensureWeaponSlots" in source
    assert "formatWeaponSkillLabel" in source
    assert "`${baseName}(${specialtyName})`" in source


def test_character_editor_weapon_skills_expand_all_catalog_specialties_and_match_exact_type():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    choices_function = source[
        source.index("function getWeaponSkillChoices") : source.index("function isWeaponSkillKey")
    ]
    success_function = source[
        source.index("function findSkillSuccessByWeaponSkill") : source.index("function openEditor")
    ]

    assert "SKILL_CATALOG.forEach" in choices_function
    assert "catalog.specialties.forEach" in choices_function
    assert 'label: formatWeaponSkillChoiceLabel(catalog.key, specialty.key)' in choices_function
    assert "格斗(斗殴)" in source
    assert "格斗（斗殴）" not in source
    assert "const byKey = skills.find" not in success_function
    assert "return weapon.skillKey && weapon.specialtyKey ? weaponSkillBaseFallback(weapon.skillKey) : 0" in success_function
    assert "function weaponSkillBaseFallback" in source
    assert 'if (skillKey === "fighting") return 1;' in source


def test_character_editor_empty_weapon_rows_use_blank_defaults():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    empty_weapon_function = source[
        source.index("function createEmptyWeapon") : source.index("function weaponSkillOptions")
    ]
    render_row_function = source[
        source.index("function renderWeaponRow") : source.index("function createEmptyWeapon")
    ]
    success_function = source[
        source.index("function findSkillSuccessByWeaponSkill") : source.index("function weaponSkillBaseFallback")
    ]

    assert 'skill: "-"' in empty_weapon_function
    assert 'skillKey: ""' in empty_weapon_function
    assert 'specialtyKey: ""' in empty_weapon_function
    assert "impale: null" in empty_weapon_function
    assert 'attacks: ""' in empty_weapon_function
    assert '<option value="">-</option>' in source
    assert '<option value="" ${weapon.impale === null ? "selected" : ""}>-</option>' in render_row_function
    assert "${success}" in render_row_function
    assert 'return "";' in success_function


def test_character_editor_skill_spending_counts_explicit_allocations_only():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    spending_function = source[
        source.index("function calculateEditorSkillPointSpending") : source.index("function autoAllocateEditorOccupationSkills")
    ]
    assert "data-skill-occupation-points" in spending_function
    assert "data-skill-interest-points" in spending_function
    assert "skill.value - skill.base" not in spending_function


def test_character_editor_skill_readonly_columns_render_as_text_and_refresh_remaining_points():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    render_function = source[
        source.index("function renderSkillTable") : source.index("function buildSkillSpecialtyButton")
    ]
    row_refresh_function = source[
        source.index("function refreshSkillRowCalculations") : source.index("function enforceSkillPointBudgets")
    ]

    assert '<span class="character-skill-value-cell" data-skill-base="${rowId}">${skill.base}</span>' in render_function
    assert "readonly data-skill-base" not in render_function
    assert "readonly data-skill-success" not in render_function
    assert "readonly data-skill-hard" not in render_function
    assert "readonly data-skill-extreme" not in render_function
    assert ".textContent = String(success)" in row_refresh_function
    assert "refreshSkillPointSummary();" in row_refresh_function


def test_character_editor_custom_skill_has_name_input_and_save_reads_it():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "frontend" / "src" / "js" / "character-sheet.ts").read_text(encoding="utf-8")

    render_function = source[
        source.index("function renderSkillTable") : source.index("function buildSkillSpecialtyButton")
    ]
    read_function = source[
        source.index("function readChecklistSkills") : source.index("function readSkillRowNumber")
    ]

    assert 'data-custom-skill-name="${rowId}"' in render_function
    assert 'placeholder="输入自定义技能"' in render_function
    assert "readCustomSkillName(row)" in read_function


def test_cthulhu_mythos_skill_is_special_category():
    project_root = Path(__file__).resolve().parents[1]
    catalog = json.loads((project_root / "data" / "config" / "character_skills.json").read_text(encoding="utf-8"))
    by_key = {skill["key"]: skill for skill in catalog["skills"]}

    assert by_key["cthulhuMythos"]["category"] == "特殊"


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
