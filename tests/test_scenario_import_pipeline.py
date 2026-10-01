from pathlib import Path

from trpg_server.agents.vector_store import EmbeddedVectorStore
from trpg_server.scenario_import_pipeline import ScenarioImportPipeline
from trpg_server.scenario_import_jobs import ImportJobStore


class FakeEmbedding:
    dimensions = 2

    def embed(self, texts):
        return [[float(len(text)), 1.0] for text in texts]


def test_direct_import_chunks_by_heading_without_scene_cards(tmp_path):
    store = ImportJobStore(tmp_path / "jobs")
    job = store.create(owner_id="1", filename="large.txt", metadata={"title": "Chunked"})
    source = Path(store.root) / job["id"] / "source" / "large.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# Scene A\n" + ("A" * 1200) + "\n\n# Scene B\n" + ("B" * 1200), encoding="utf-8")

    vector_store = EmbeddedVectorStore(tmp_path / "vectors")
    result = ScenarioImportPipeline(
        store,
        {
            "OCR_ENABLED": False,
            "EMBEDDING_PROVIDER": FakeEmbedding(),
            "VECTOR_STORE": vector_store,
        },
    ).run(job["id"])

    assert result["status"] == "done"
    assert result["preview"]["import_mode"] == "direct"
    # 直接导入按标题切块，不再生成可编辑的场景卡。
    assert result["preview"]["modules"] == []
    assert result["stage_meta"]["totalChunks"] == 2
    assert result["stage_meta"]["processedChunks"] == 2
    assert vector_store.count({"scenario_id": str(job["script_id"])}) == 2
