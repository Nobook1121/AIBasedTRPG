from trpg_server.agents.knowledge_base import KnowledgeBaseService, build_knowledge_chunks, load_knowledge_index
from trpg_server.scenario_store import save_scenario_record


def test_build_chunks_contains_versioned_metadata_and_visibility():
    chunks = build_knowledge_chunks(
        {
            "id": "case-1",
            "scenario_version": "2",
            "modules": [
                {
                    "id": "scene-1",
                    "module_type": "scene",
                    "title": "Library",
                    "summary": "A locked library",
                    "content": "The brass key opens the library.",
                    "visibility": "public",
                    "spoiler_level": 1,
                }
            ],
        }
    )
    assert chunks[0].scenario_id == "case-1"
    assert chunks[0].scenario_version == "2"
    assert chunks[0].scene_id == "scene-1"
    assert chunks[0].card_type == "scene"
    assert chunks[0].text == "The brass key opens the library."


def test_search_filters_scenario_version_scene_and_spoiler_before_scoring(tmp_path):
    scenarios = tmp_path / "scenarios"
    rooms = tmp_path / "rooms"
    scenarios.mkdir()
    room = rooms / "room-1"
    room.mkdir(parents=True)
    (room / "info.json").write_text(
        '{"id":"room-1","scenario_id":"case-1","scenario_version":"2","active_scene_id":"scene-1","spoiler_level":1}',
        encoding="utf-8",
    )
    service = KnowledgeBaseService(
        rooms_dir=rooms,
        scenarios={
            "case-1": {
                "id": "case-1",
                "scenario_version": "2",
                "modules": [
                    {"id": "scene-1", "module_type": "scene", "content": "brass key library", "spoiler_level": 1},
                    {"id": "scene-2", "module_type": "scene", "content": "brass key garden", "spoiler_level": 0},
                    {"id": "scene-1-old", "scene_id": "scene-1", "module_type": "scene", "content": "brass key old", "scenario_version": "1", "spoiler_level": 0},
                    {"id": "scene-1-secret", "module_type": "scene", "content": "brass key secret", "spoiler_level": 2},
                ],
            }
        },
    )

    result = service.search("room-1", "brass key", top_k=10)

    assert [item["text"] for item in result] == ["brass key library"]


def test_saving_scenario_persists_versioned_knowledge_index(tmp_path):
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    descriptor = save_scenario_record(scenarios, {"id": 9, "scenario_version": "3", "modules": [{"id": "scene", "module_type": "scene", "content": "lighthouse"}]})
    chunks = load_knowledge_index(descriptor, "3")
    assert [chunk.text for chunk in chunks] == ["lighthouse"]
