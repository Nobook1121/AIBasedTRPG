from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_CONTROLLER_JS = PROJECT_ROOT / "js" / "controllers" / "ScenarioController.js"
SCENARIO_VIEW_JS = PROJECT_ROOT / "js" / "views" / "ScenarioView.js"
SCENARIO_MODEL_JS = PROJECT_ROOT / "js" / "models" / "ScenarioModel.js"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_edit_scenario_saves_through_backend_api():
    source = _read(SCENARIO_CONTROLLER_JS)

    assert "this.model.updateScenario(id, scenarioData)" in source
    assert "直接更新本地剧本数据" not in source


def test_scenario_frontend_uses_canonical_cover_asset_prefix():
    combined = "\n".join(
        [
            _read(SCENARIO_CONTROLLER_JS),
            _read(SCENARIO_VIEW_JS),
            _read(SCENARIO_MODEL_JS),
        ]
    )

    assert "/assets/scenario_covers/default_cover.png" in combined
    assert "'/scenario_covers/default_cover.png'" not in combined
    assert '"/scenario_covers/default_cover.png"' not in combined
