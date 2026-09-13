from trpg_server.agents.room_state import (
    append_room_event,
    load_room_state,
    project_room_state,
    save_room_state,
)


def test_room_state_defaults_and_atomic_round_trip(tmp_path):
    room_dir = tmp_path / "room-1"
    room_dir.mkdir()

    state = load_room_state(room_dir)
    assert state["active_scene_id"] is None
    assert state["triggered_event_ids"] == []
    assert state["event_log"] == []

    state["active_scene_id"] = "scene-1"
    saved = save_room_state(room_dir, state)
    assert saved["active_scene_id"] == "scene-1"
    assert load_room_state(room_dir)["active_scene_id"] == "scene-1"


def test_append_event_and_projection_keep_only_current_context(tmp_path):
    room_dir = tmp_path / "room-1"
    room_dir.mkdir()
    append_room_event(room_dir, {"kind": "clue", "content": "found key"})
    append_room_event(room_dir, {"kind": "travel", "content": "entered library"})

    state = load_room_state(room_dir)
    projected = project_room_state(
        state,
        {"room": {"id": "room-1"}, "scenario": {"active_scene_id": "scene-2"}},
    )

    assert len(state["event_log"]) == 2
    assert projected["active_scene_id"] == "scene-2"
    assert projected["event_log"][-1]["content"] == "entered library"
    assert "room-1" not in projected

