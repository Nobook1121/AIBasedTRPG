from trpg_server.agents.structured_output import parse_kp_response, validate_state_updates


def test_parse_kp_response_accepts_fenced_json_and_normalizes_fields():
    result = parse_kp_response(
        "```json\n"
        '{"narration":"门开了","options":["进入"],"state_updates":{"items":["key"]},'
        '"next_scene":"scene-2","npc_actions":[{"id":"guard","action":"待命"}],"extra":true}'
        "\n```"
    )

    assert result is not None
    assert result.narration == "门开了"
    assert result.options == ["进入"]
    assert result.state_updates == {"items": ["key"]}
    assert result.next_scene == "scene-2"
    assert result.npc_actions == [{"id": "guard", "action": "待命"}]


def test_validate_state_updates_rejects_unknown_fields_and_unlisted_scene():
    result = validate_state_updates(
        {"items": ["key"], "admin": True, "active_scene_id": "scene-x"},
        {},
        {"scene_manifest": [{"id": "scene-1"}]},
    )

    assert result == {"items": ["key"]}

