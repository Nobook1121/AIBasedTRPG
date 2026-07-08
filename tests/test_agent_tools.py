from trpg_server.agents.profiles import DEFAULT_KP_TOOLS
from trpg_server.agents.tools import default_tool_registry
from trpg_server.agents.tools.dice import roll_coc_check, roll_room_check

import json

from trpg_server.agents.context import AgentRequestContext
from trpg_server.agents.memory import read_room_memory, remember_room_fact
from trpg_server.agents.tools.room import (
    get_room_character_cards,
    get_room_scenario_context,
    get_room_snapshot,
)


def test_coc_check_regular_success_with_fixed_rng():
    result = roll_coc_check(
        {
            "skill": "锁匠",
            "target": 45,
            "difficulty": "regular",
            "reason": "打开地下室门锁",
        },
        rng=lambda sides: 34,
    )

    assert result["roll"] == 34
    assert result["target"] == 45
    assert result["threshold"] == 45
    assert result["success"] is True
    assert result["success_level"] == "regular"
    assert "锁匠" in result["summary"]


def test_coc_check_hard_failure_uses_half_threshold():
    result = roll_coc_check(
        {"skill": "侦查", "target": 50, "difficulty": "hard"},
        rng=lambda sides: 31,
    )

    assert result["threshold"] == 25
    assert result["success"] is False
    assert result["success_level"] == "failure"


def test_coc_check_extreme_success_uses_fifth_threshold():
    result = roll_coc_check(
        {"skill": "图书馆使用", "target": 80, "difficulty": "extreme"},
        rng=lambda sides: 16,
    )

    assert result["threshold"] == 16
    assert result["success"] is True
    assert result["success_level"] == "extreme"


def test_coc_check_rejects_invalid_target():
    result = roll_coc_check({"skill": "锁匠", "target": 0}, rng=lambda sides: 1)

    assert result["error"] == "target must be between 1 and 100"


def _context_with_check_member(tmp_path, member):
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps({"id": "room-1", "members": [member]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return AgentRequestContext(room_id="room-1", room_dir=room_dir, agent_id="kp")


def test_room_check_reads_skill_from_bound_character_by_username(tmp_path):
    skill_name = "\u4fa6\u5bdf"
    context = _context_with_check_member(
        tmp_path,
        {
            "username": "testplayer",
            "status": "active",
            "character_card": {
                "name": "\u8c03\u67e5\u5458",
                "skills": [{"name": skill_name, "value": 60}],
            },
        },
    )

    result = roll_room_check({"player_name": "testplayer", "name": skill_name}, context, rng=lambda sides: 30)

    assert result["roll"] == 30
    assert result["target"] == 60
    assert result["threshold"] == 60
    assert result["success"] is True
    assert result["summary"] == "\u4fa6\u5bdf d%: [30] = 30 / 60 \u6210\u529f"


def test_room_check_applies_difficulty_and_adjustment(tmp_path):
    skill_name = "\u4fa6\u5bdf"
    context = _context_with_check_member(
        tmp_path,
        {
            "username": "testplayer",
            "status": "active",
            "character_card": {
                "name": "\u8c03\u67e5\u5458",
                "skills": [{"name": skill_name, "value": 60}],
            },
        },
    )

    result = roll_room_check(
        {"player_name": "testplayer", "name": skill_name, "difficulty": "\u56f0\u96be", "adjustment": "+10"},
        context,
        rng=lambda sides: 40,
    )

    assert result["base_target"] == 60
    assert result["threshold"] == 40
    assert result["success"] is True
    assert result["summary"] == "\u56f0\u96be\u4fa6\u5bdf d%: [40] = 40 / 40 \u6210\u529f"


def test_room_check_reads_attribute_alias_from_bound_character(tmp_path):
    context = _context_with_check_member(
        tmp_path,
        {
            "username": "testplayer",
            "status": "active",
            "character_card": {
                "name": "\u8c03\u67e5\u5458",
                "attributes": {"DEX": 55},
                "skills": [],
            },
        },
    )

    result = roll_room_check(
        {"player_name": "testplayer", "name": "\u654f\u6377", "difficulty": "\u6781\u96be"},
        context,
        rng=lambda sides: 12,
    )

    assert result["base_target"] == 55
    assert result["threshold"] == 11
    assert result["success"] is False
    assert result["summary"] == "\u6781\u96be\u654f\u6377 d%: [12] = 12 / 11 \u5931\u8d25"


def test_room_check_returns_error_for_missing_bound_character(tmp_path):
    context = _context_with_check_member(tmp_path, {"username": "testplayer", "status": "active"})

    result = roll_room_check({"player_name": "testplayer", "name": "\u4fa6\u5bdf"}, context, rng=lambda sides: 1)

    assert result["error"] == "player testplayer has no bound character card"


def test_kp_default_tools_include_room_check_function():
    registry = default_tool_registry()

    assert "check.roll_room_check" in DEFAULT_KP_TOOLS
    assert registry.get("check.roll_room_check") is not None


def test_frontend_registers_check_command():
    manager_source = open("frontend/src/tools/toolManager.ts", encoding="utf-8").read()
    chat_source = open("frontend/src/js/chat.ts", encoding="utf-8").read()

    assert '"/check"' in manager_source
    assert "handleCheckCommand" in manager_source
    assert "/check {*\u73a9\u5bb6\u540d} {*\u6280\u80fd/\u5c5e\u6027\u540d}" in chat_source


def test_kp_prompt_requires_room_check_function():
    prompt = open("data/config/roles/kp.md", encoding="utf-8").read()

    assert "check.roll_room_check" in prompt
    assert "/check {*\u73a9\u5bb6\u540d} {*\u6280\u80fd/\u5c5e\u6027\u540d}" in prompt


def test_room_scenario_context_loads_current_room_scenario(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps({"id": "room-1", "scenario_id": 7, "members": []}),
        encoding="utf-8",
    )
    (scenarios_dir / "haunted.json").write_text(
        json.dumps(
            {
                "id": 7,
                "title": "雨夜来客",
                "description": "暴雨中的宅邸调查。",
                "scenes": [{"id": "hall", "title": "门厅", "description": "潮湿的地毯。"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir, scenarios_dir=scenarios_dir)

    result = get_room_scenario_context({"query": "门厅"}, context)

    assert result["scenario"]["title"] == "雨夜来客"
    assert result["matches"][0]["title"] == "门厅"


def test_room_character_cards_returns_active_bound_cards(tmp_path):
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps(
            {
                "id": "room-1",
                "members": [
                    {
                        "user_id": 1,
                        "username": "alice",
                        "status": "active",
                        "character_card": {
                            "id": "investigator",
                            "name": "林见山",
                            "background": {"story": "失踪记者。"},
                            "skills": [{"name": "锁匠", "value": 45}],
                        },
                        "character_state": {"current_hp": 10, "current_san": 55},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir)

    result = get_room_character_cards({}, context)

    assert result["members"][0]["username"] == "alice"
    assert result["members"][0]["character_card"]["name"] == "林见山"
    assert result["members"][0]["character_state"]["current_san"] == 55


def test_room_memory_write_and_read(tmp_path):
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir, agent_id="kp")

    remembered = remember_room_fact(
        {"kind": "npc_state", "content": "图书管理员开始怀疑调查员。", "importance": 3},
        context,
    )
    memory = read_room_memory({"query": "图书管理员", "limit": 5}, context)

    assert remembered["stored"] is True
    assert memory["items"][0]["content"] == "图书管理员开始怀疑调查员。"


def test_room_snapshot_omits_full_character_card_and_scenario_details(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps(
            {
                "id": "room-1",
                "name": "test room",
                "scenario_id": 7,
                "scenario_title": "Long Life Figurine",
                "members": [
                    {
                        "user_id": 9,
                        "username": "ADMIN",
                        "status": "active",
                        "is_active": True,
                        "character_card": {
                            "id": "investigator-1",
                            "name": "Wu Mingshan",
                            "attributes": {"DEX": 55},
                            "skills": [{"name": "Spot Hidden", "value": 70}],
                            "background": {"story": "Long character history"},
                        },
                        "character_state": {"current_hp": 15, "current_san": 50},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (scenarios_dir / "scenario.json").write_text(
        json.dumps(
            {
                "id": 7,
                "title": "Long Life Figurine",
                "background": "Large background should not be in snapshot",
                "scenes": [{"id": 1, "content": "Large scene body should not be in snapshot"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir, scenarios_dir=scenarios_dir)

    result = get_room_snapshot({}, context)
    serialized = json.dumps(result, ensure_ascii=False)

    assert result["members"][0]["character"]["name"] == "Wu Mingshan"
    assert result["members"][0]["character_state"]["current_san"] == 50
    assert "skills" not in serialized
    assert "attributes" not in serialized
    assert "Spot Hidden" not in serialized
    assert "DEX" not in serialized
    assert "Large scene body should not be in snapshot" not in serialized
    assert "Large background should not be in snapshot" not in serialized


def test_room_snapshot_returns_bound_scenario_and_character_cards(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps(
            {
                "id": "room-1",
                "name": "测试房间",
                "scenario_id": 1776085966397,
                "scenario_title": "长生俑",
                "members": [
                    {
                        "user_id": 9,
                        "username": "ADMIN",
                        "status": "active",
                        "is_active": True,
                        "character_card": {
                            "id": "investigator-1",
                            "name": "吴明山",
                            "background": {"story": "失踪记者。"},
                            "skills": [{"skillKey": "locksmith", "name": "锁匠", "value": 45}],
                        },
                        "character_state": {"current_hp": 15, "current_san": 50},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (scenarios_dir / "长生俑.json").write_text(
        json.dumps(
            {
                "id": 1776085966397,
                "title": "长生俑",
                "background": "秦俑与长生药的现代调查。",
                "scenes": [{"id": 1, "content": "西安高铁站。冯教授迎接调查员。"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (room_dir / "agent_memory.json").write_text(
        json.dumps(
            [{"id": "memory-1", "kind": "fact", "content": "ADMIN 已经找到门厅暗格。", "importance": 4}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir, scenarios_dir=scenarios_dir)

    result = get_room_snapshot({}, context)

    assert result["room"]["id"] == "room-1"
    assert result["scenario"]["id"] == 1776085966397
    assert result["scenario"]["title"] == "长生俑"
    assert result["scenario"]["available_sections"]["scenes"] == 1
    assert result["members"][0]["character"]["name"] == "吴明山"
    assert result["members"][0]["character_state"]["current_san"] == 50
    assert result["memory"]["items"][0]["content"] == "ADMIN 已经找到门厅暗格。"
    assert "skills" not in json.dumps(result, ensure_ascii=False)
