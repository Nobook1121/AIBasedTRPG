from trpg_server.agents.tools.dice import roll_coc_check

import json

from trpg_server.agents.context import AgentRequestContext
from trpg_server.agents.memory import read_room_memory, remember_room_fact
from trpg_server.agents.tools.room import get_room_character_cards, get_room_scenario_context


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
