from pathlib import Path

from trpg_server.agents.vector_store import EmbeddedVectorStore
from trpg_server.scenario_import_pipeline import ScenarioImportPipeline
from trpg_server.scenario_import_jobs import ImportJobStore


class FakeEmbedding:
    dimensions = 2

    def embed(self, texts):
        return [[float(len(text)), 1.0] for text in texts]


def test_direct_import_processes_each_chunk_and_reports_chunk_progress(tmp_path):
    store = ImportJobStore(tmp_path / "jobs")
    job = store.create(owner_id="1", filename="large.txt", metadata={"title": "Chunked"})
    source = Path(store.root) / job["id"] / "source" / "large.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# Scene A\n" + ("A" * 1200) + "\n\n# Scene B\n" + ("B" * 1200), encoding="utf-8")
    analyzed = []

    def analyzer(chunk, index, total):
        analyzed.append((index, total, chunk.text))
        return {
            "card_type": "scene",
            "scene_id": f"scene-{index}",
            "spoiler_level": 2,
            "visibility": "kp_only",
            "unlock_condition": "调查后",
            "summary": f"chunk {index}",
        }

    vector_store = EmbeddedVectorStore(tmp_path / "vectors")
    result = ScenarioImportPipeline(
        store,
        {
            "OCR_ENABLED": False,
            "EMBEDDING_PROVIDER": FakeEmbedding(),
            "VECTOR_STORE": vector_store,
            "SCENARIO_CHUNK_ANALYZER": analyzer,
        },
    ).run(job["id"])

    assert result["status"] == "done"
    assert len(analyzed) >= 2
    assert result["stage_meta"]["totalChunks"] == len(analyzed)
    assert result["stage_meta"]["processedChunks"] == len(analyzed)
    assert result["preview"]["import_mode"] == "direct"
    assert all(module["card_type"] == "scene" for module in result["preview"]["modules"])
    assert all(module["embedding"] for module in result["preview"]["modules"])
    assert vector_store.count({"scenario_id": str(job["script_id"])}) == len(analyzed)
