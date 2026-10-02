import json

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


def test_search_fallback_advances_with_room_cursor_instead_of_repeating(tmp_path):
    scenarios = tmp_path / "scenarios"
    rooms = tmp_path / "rooms"
    scenarios.mkdir()
    room = rooms / "room-1"
    room.mkdir(parents=True)
    (room / "info.json").write_text(
        '{"id":"room-1","scenario_id":"case-1","scenario_version":"1","spoiler_level":0}',
        encoding="utf-8",
    )
    service = KnowledgeBaseService(
        rooms_dir=rooms,
        scenarios={
            "case-1": {
                "id": "case-1",
                "scenario_version": "1",
                "modules": [
                    {"id": f"chunk-{index}", "module_type": "lore", "content": f"alpha {index}"}
                    for index in range(1, 7)
                ],
            }
        },
    )

    # 无任何词法/向量命中的泛化输入会走兜底路径；此时应优先返回尚未消费过的块，
    # 使连续检索随剧情推进而变化，而不是每次都重复开头几段。
    first = service.search("room-1", "zzzzzz", top_k=3)
    second = service.search("room-1", "zzzzzz", top_k=3)

    assert [item["chunk_id"] for item in first] == ["chunk-1", "chunk-2", "chunk-3"]
    assert [item["chunk_id"] for item in second] == ["chunk-4", "chunk-5", "chunk-6"]
    assert (room / "knowledge_cursor.json").exists()


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


def _sectioned_service(tmp_path, modules):
    rooms = tmp_path / "rooms"
    room = rooms / "room-1"
    room.mkdir(parents=True)
    (room / "info.json").write_text(
        '{"id":"room-1","scenario_id":"case-1","scenario_version":"1","spoiler_level":0}',
        encoding="utf-8",
    )
    service = KnowledgeBaseService(
        rooms_dir=rooms,
        scenarios={"case-1": {"id": "case-1", "scenario_version": "1", "modules": modules}},
    )
    return service, room


def test_search_backfills_section_context_from_sibling_chunks(tmp_path):
    service, _room = _sectioned_service(
        tmp_path,
        [
            {"id": "chunk-0001", "module_type": "lore", "content": "第一部分：铜钥匙", "metadata": {"section": "图书馆", "title": "图书馆"}},
            {"id": "chunk-0002", "module_type": "lore", "content": "第二部分：书架暗门", "metadata": {"section": "图书馆", "title": "图书馆"}},
            {"id": "chunk-0003", "module_type": "lore", "content": "花园里的玫瑰", "metadata": {"section": "花园", "title": "花园"}},
        ],
    )

    result = service.search("room-1", "书架暗门", top_k=5)

    # 命中子块所属的整章只返回一条结果，且把同章节的相邻子块合并回填。
    assert len(result) == 1
    assert result[0]["chunk_ids"] == ["chunk-0001", "chunk-0002"]
    assert "铜钥匙" in result[0]["text"]
    assert "书架暗门" in result[0]["text"]


def test_search_bm25_prefers_rare_term_over_common_term(tmp_path):
    service, _room = _sectioned_service(
        tmp_path,
        [
            {"id": "chunk-0001", "module_type": "lore", "content": "魔法 魔法 魔法 魔法", "metadata": {"section": "甲", "title": "甲"}},
            {"id": "chunk-0002", "module_type": "lore", "content": "魔法 禁忌咒语", "metadata": {"section": "乙", "title": "乙"}},
        ],
    )

    result = service.search("room-1", "禁忌咒语 魔法", top_k=5)

    # 稀有词（禁忌咒语）的 IDF 更高，含稀有词的章节应排在只堆砌高频词的前面。
    assert result[0]["chunk_ids"] == ["chunk-0002"]


def test_search_records_round_history_for_sticky_cooldown(tmp_path):
    service, room = _sectioned_service(
        tmp_path,
        [
            {"id": f"chunk-{index}", "module_type": "lore", "content": f"alpha {index}"}
            for index in range(1, 5)
        ],
    )

    service.search("room-1", "zzzzzz", top_k=2)

    data = json.loads((room / "knowledge_cursor.json").read_text(encoding="utf-8"))
    assert data["scenario"] == "case-1@1"
    assert len(data["rounds"]) == 1
    assert len(data["rounds"][0]) == 2
