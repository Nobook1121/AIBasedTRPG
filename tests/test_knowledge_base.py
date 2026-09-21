from trpg_server.agents.embedding_provider import HashedTokenEmbedding
from trpg_server.agents.knowledge_base import KnowledgeBaseService, build_knowledge_chunks, load_knowledge_index, persist_knowledge_index
from trpg_server.agents.vector_store import EmbeddedVectorStore
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


def test_search_fuses_vector_results_after_hard_filters(tmp_path):
    scenarios = tmp_path / "scenarios"
    rooms = tmp_path / "rooms"
    scenarios.mkdir()
    room = rooms / "room-1"
    room.mkdir(parents=True)
    (room / "info.json").write_text(
        '{"id":"room-1","scenario_id":"case-1","scenario_version":"1.0.0","active_scene_id":"scene-1","spoiler_level":1}',
        encoding="utf-8",
    )

    class FakeEmbedding:
        configured = True
        dimensions = 2

        def embed(self, texts):
            assert texts == ["brass key"]
            return [[1.0, 0.0]]

    class FakeVectorStore:
        def search(self, collection, vector, limit=5):
            assert collection == "scenario_case-1_1.0.0"
            assert vector == [1.0, 0.0]
            return [
                {"id": "secret", "score": 0.99, "payload": {"module_id": "scene-secret"}},
                {"id": "scene-1", "score": 0.8, "payload": {"module_id": "scene-1"}},
            ]

    service = KnowledgeBaseService(
        rooms_dir=rooms,
        scenarios={
            "case-1": {
                "id": "case-1",
                "scenario_version": "1.0.0",
                "modules": [
                    {"id": "scene-1", "module_type": "scene", "content": "brass key library", "spoiler_level": 0},
                    {"id": "scene-secret", "module_type": "scene", "content": "brass key secret", "spoiler_level": 2},
                ],
            }
        },
        vector_store=FakeVectorStore(),
        embedding_provider=FakeEmbedding(),
    )

    result = service.search("room-1", "brass key", top_k=5)

    assert [item["chunk_id"] for item in result] == ["scene-1"]
    assert result[0]["score_components"]["vector"] == 0.8


def test_saving_scenario_persists_versioned_knowledge_index(tmp_path):
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    descriptor = save_scenario_record(scenarios, {"id": 9, "scenario_version": "3", "modules": [{"id": "scene", "module_type": "scene", "content": "lighthouse"}]})
    chunks = load_knowledge_index(descriptor, "3")
    assert [chunk.text for chunk in chunks] == ["lighthouse"]


def test_persisted_json_index_is_idempotently_written_to_embedded_store(tmp_path):
    descriptor = tmp_path / "scenarios" / "scenario-9" / "scenario.json"
    store = EmbeddedVectorStore(tmp_path / "vectors")
    provider = HashedTokenEmbedding(32)
    version_one = {
        "id": "9",
        "scenario_version": "1",
        "modules": [{"id": "scene", "module_type": "scene", "content": "old lighthouse"}],
    }
    version_two = {
        "id": "9",
        "scenario_version": "2",
        "modules": [{"id": "scene", "module_type": "scene", "content": "new lighthouse"}],
    }

    persist_knowledge_index(descriptor, version_one, vector_store=store, embedding_provider=provider)
    persist_knowledge_index(descriptor, version_one, vector_store=store, embedding_provider=provider)
    persist_knowledge_index(descriptor, version_two, vector_store=store, embedding_provider=provider)

    assert store.count({"scenario_id": "9", "scenario_version": "1"}) == 1
    assert store.count({"scenario_id": "9", "scenario_version": "2"}) == 1
    assert store.count({"scenario_id": "9"}) == 2
