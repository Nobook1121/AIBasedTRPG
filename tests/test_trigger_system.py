import json
from pathlib import Path

from trpg_server.agents.context import AgentRequestContext
from trpg_server.agents.tools.trigger import reveal_scenario_trigger
from trpg_server.agents.trigger_system import (
    persist_uploaded_resource,
    validate_trigger,
)


class Upload:
    filename = "clue.txt"
    mimetype = "text/plain"

    def __init__(self, data=b"secret"):
        self.data = data

    def read(self):
        return self.data


def _scenario(tmp_path: Path):
    resource = persist_uploaded_resource(tmp_path, 10, Upload(), "A secret clue")
    return {
        "id": 10,
        "scenario_version": "1.0.0",
        "trigger_cards": [{
            "id": "trg-1",
            "scriptId": "10",
            "scriptVersion": "1.0.0",
            "cardType": "trigger",
            "sceneId": "scene-1",
            "spoilerLevel": 1,
            "visibility": "player_visible",
            "attachments": [{
                "triggerId": "trg-1",
                "resourceRef": resource,
                "condition": {"type": "clue_found", "clueId": "clue-1"},
                "spoilerLevel": 1,
                "visibility": "player_visible",
                "repeatable": False,
                "enabled": True,
            }],
        }],
    }


def test_trigger_validation_enforces_condition_and_repeatability(tmp_path):
    scenario = _scenario(tmp_path)
    state = {"scenario_version": "1.0.0", "active_scene_id": "scene-1", "clues": []}
    assert validate_trigger("trg-1", state, scenario)["reason"] == "condition_not_met"
    state["clues"] = ["clue-1"]
    assert validate_trigger("trg-1", state, scenario)["ok"] is True
    state["triggeredFiles"] = ["trg-1"]
    assert validate_trigger("trg-1", state, scenario)["reason"] == "already_triggered"


def test_trigger_validation_rejects_wrong_script_version(tmp_path):
    scenario = _scenario(tmp_path)
    state = {"scenario_version": "2.0.0", "active_scene_id": "scene-1", "clues": ["clue-1"]}
    assert validate_trigger("trg-1", state, scenario)["reason"] == "scenario_version_mismatch"


def _library_scenario() -> dict:
    """触发器资源库（trigger_cards）场景，无场景栏位触发器。"""
    return {
        "id": 10,
        "scenario_version": "1.0.0",
        "modules": [],
        "trigger_cards": [
            {
                "id": "trg-1",
                "scriptId": "10",
                "scriptVersion": "1.0.0",
                "cardType": "trigger",
                "text": "图书馆线索",
                "attachments": [
                    {
                        "triggerId": "trg-1",
                        "resourceRef": {
                            "type": "richtext",
                            "path": "assets/clue.txt",
                            "url": "/assets/scenarios/scenario-10/assets/clue.txt",
                            "alt": "线索",
                            "mime": "text/plain",
                            "size": 6,
                            "hash": "abc123",
                            "content": "秘密线索内容",
                        },
                        "condition": {"type": "custom"},
                        "spoilerLevel": 1,
                        "visibility": "player_visible",
                        "repeatable": False,
                        "enabled": True,
                    }
                ],
            }
        ],
    }


def _write_library_scenario(scenarios_dir: Path) -> None:
    scenario_dir = scenarios_dir / "scenario-10"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario.json").write_text(
        json.dumps(_library_scenario(), ensure_ascii=False), encoding="utf-8"
    )


def _library_context(tmp_path: Path) -> AgentRequestContext:
    scenarios_dir = tmp_path / "scenarios"
    _write_library_scenario(scenarios_dir)
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps({"id": "room-1", "scenario_id": 10, "scenario_version": "1.0.0"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (room_dir / "state.json").write_text(json.dumps({"active_scene_id": None}), encoding="utf-8")
    return AgentRequestContext(room_id="room-1", room_dir=room_dir, scenarios_dir=scenarios_dir, agent_id="kp")


def test_trigger_tool_reveals_library_trigger_card(tmp_path):
    # KP 通过工具应能揭示「触发器资源库」中的卡片，而不仅是场景栏位触发器。
    context = _library_context(tmp_path)

    result = reveal_scenario_trigger({"trigger_id": "trg-1"}, context)

    assert result.get("triggered") is True
    assert result["direct_message"]["content"] == "秘密线索内容"


def test_trigger_tool_rejects_unapproved_library_trigger(tmp_path):
    # 资源库触发器同样受剧本版本校验约束，不能绕过规则任意揭示。
    context = _library_context(tmp_path)
    (context.room_dir / "info.json").write_text(
        json.dumps({"id": "room-1", "scenario_id": 10, "scenario_version": "2.0.0"}, ensure_ascii=False),
        encoding="utf-8",
    )

    result = reveal_scenario_trigger({"trigger_id": "trg-1"}, context)

    assert "error" in result
    assert result.get("reason") == "scenario_version_mismatch"
