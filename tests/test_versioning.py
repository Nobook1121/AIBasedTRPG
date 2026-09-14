from trpg_server.agents.versioning import (
    bind_room_to_scenario_version,
    next_scenario_version,
    validate_version_migration,
    migrate_room_binding,
)
from trpg_server.scenario_store import load_scenario_by_id, save_scenario_record


def test_next_scenario_version_increments_numeric_release():
    assert next_scenario_version("7") == "8"
    assert next_scenario_version("draft") == "1"


def test_room_binding_pins_version_and_migration_requires_mapping():
    room = bind_room_to_scenario_version({"id": "r1", "scenario_id": "s1"}, {"id": "s1", "scenario_version": "3"})
    assert room["scenario_version"] == "3"
    assert validate_version_migration({"scene-1": "scene-a"}, {"scene-1"}, {"scene-a"})["valid"] is True
    assert validate_version_migration({}, {"scene-1"}, {"scene-a"})["valid"] is False


def test_saved_versions_keep_old_room_snapshot_isolated(tmp_path):
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    save_scenario_record(scenarios, {"id": 7, "title": "Case", "scenario_version": "1", "modules": [{"id": "scene-1", "module_type": "scene", "content": "old room"}]})
    save_scenario_record(scenarios, {"id": 7, "title": "Case", "scenario_version": "2", "modules": [{"id": "scene-1", "module_type": "scene", "content": "new room"}]})

    _, old = load_scenario_by_id(scenarios, 7, scenario_version="1")
    _, latest = load_scenario_by_id(scenarios, 7, scenario_version="2")
    assert old["modules"][0]["content"] == "old room"
    assert latest["modules"][0]["content"] == "new room"


def test_migrate_room_binding_is_atomic_and_maps_version():
    room = migrate_room_binding(
        {"id": "r1", "scenario_id": 7, "scenario_version": "1"},
        {"id": 7, "scenario_version": "2"},
        {"scene-1": "scene-a"},
        {"scene-1"},
        {"scene-a"},
    )
    assert room["scenario_version"] == "2"
    assert room["migration"]["from_version"] == "1"
