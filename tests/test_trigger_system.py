from pathlib import Path

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
