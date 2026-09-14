from trpg_server.agents.prompt_builder import build_prompt_layers


def test_prompt_layers_keep_static_prefix_before_dynamic_room_data():
    result = build_prompt_layers(
        global_rules="GLOBAL",
        scenario={"id": "scenario-1", "version": "3", "core": "CORE"},
        scene={"id": "scene-2", "version": "5", "content": "SCENE"},
        room_state={"room_id": "room-a", "active_scene_id": "scene-2", "items": ["key"]},
        history=[{"role": "assistant", "content": "old"}],
        user_input="look",
        rules_version="7",
    )

    assert [message["role"] for message in result.messages] == [
        "system",
        "system",
        "system",
        "system",
        "assistant",
        "user",
    ]
    assert result.messages[0]["content"] == "GLOBAL"
    assert "CORE" in result.messages[1]["content"]
    assert "SCENE" in result.messages[2]["content"]
    assert "room-a" in result.messages[3]["content"]
    assert result.messages[-1]["content"] == "look"
    assert result.static_prefix.index("GLOBAL") < result.static_prefix.index("CORE")
    assert result.static_prefix.index("CORE") < result.static_prefix.index("SCENE")
    assert "room-a" not in result.static_prefix


def test_prompt_cache_key_excludes_room_and_dynamic_values():
    first = build_prompt_layers(
        global_rules="GLOBAL",
        scenario={"id": "scenario-1", "version": "3", "core": "CORE"},
        scene={"id": "scene-2", "version": "5", "content": "SCENE"},
        room_state={"room_id": "room-a", "active_scene_id": "scene-2", "items": ["key"]},
        history=[],
        user_input="one",
        rules_version="7",
    )
    second = build_prompt_layers(
        global_rules="GLOBAL",
        scenario={"id": "scenario-1", "version": "3", "core": "CORE"},
        scene={"id": "scene-2", "version": "5", "content": "SCENE"},
        room_state={"room_id": "room-b", "active_scene_id": "scene-2", "items": ["torch"]},
        history=[{"role": "user", "content": "different"}],
        user_input="two",
        rules_version="7",
    )

    assert first.cache_key == second.cache_key
    assert first.static_prefix == second.static_prefix


def test_prompt_layers_place_retrieval_after_static_layers():
    result = build_prompt_layers(
        global_rules="GLOBAL",
        scenario={"id": "s", "scenario_version": "2", "core": "CORE"},
        scene={"id": "scene-1", "version": "1", "content": "SCENE"},
        room_state={"room_id": "room-1"},
        history=[],
        user_input="look",
        retrieval_results=[{"text": "The brass key is hidden here.", "spoiler_level": 0}],
    )
    assert result.messages[3]["role"] == "system"
    assert "brass key" in result.messages[3]["content"]
    assert "room-1" in result.messages[4]["content"]
    assert "scenario:s@2" in result.cache_key
