from io import BytesIO
from pathlib import Path
import time

from trpg_server.agents.vector_store import EmbeddedVectorStore
from trpg_server.app_factory import create_app
from trpg_server.scenario_import_pipeline import ScenarioImportPipeline
from trpg_server.scenario_import_jobs import ImportJobStore


class FakeEmbedding:
    dimensions = 2

    def embed(self, texts):
        return [[float(len(text)), 1.0] for text in texts]


class FakeManager:
    def is_session_current(self, user_id, token):
        return True

    def get_user_by_id(self, user_id):
        return {"id": user_id, "username": "tester", "role": "ADMIN"}


def test_import_route_returns_job_ids_and_publishes(tmp_path):
    """POST /api/scripts/import 必须回传 jobId/scriptId，前端据此轮询与发布。

    回归：前端曾按 `id` 读取该响应，导致轮询 `/api/scripts/import/undefined`
    并报「Import job not found」。
    """
    app = create_app(
        {
            "TESTING": True,
            "USER_MANAGER": FakeManager(),
            "CONFIG_DIR": tmp_path / "config",
            "KNOWLEDGE_BASES_DIR": tmp_path / "kb",
            "ROOMS_DIR": tmp_path / "rooms",
            "SCENARIOS_DIR": tmp_path / "scenarios",
            "SCENARIO_IMPORTS_DIR": tmp_path / "imports",
            "VECTOR_BACKEND": "embedded",
            "VECTOR_BACKEND_EXPLICIT": True,
            "EMBEDDED_VECTOR_DB_PATH": tmp_path / "vectors",
            "EMBEDDING_PROVIDER": FakeEmbedding(),
        }
    )
    client = app.test_client()
    with client.session_transaction() as session:
        session.update(user_id=1, username="tester", role="ADMIN", session_token="token", csrf_token="csrf")

    created = client.post(
        "/api/scripts/import",
        data={"file": (BytesIO(("# 场景\n" + "A" * 120).encode("utf-8")), "sample.md"), "title": "Sample"},
        headers={"X-CSRF-Token": "csrf"},
    )
    assert created.status_code == 202
    started = created.get_json()["data"]
    assert started["jobId"]
    assert isinstance(started["scriptId"], int)

    job = None
    for _ in range(300):
        polled = client.get(f"/api/scripts/import/{started['jobId']}")
        assert polled.status_code == 200, polled.get_json()
        job = polled.get_json()["data"]
        if job["status"] in {"done", "failed", "cancelled"}:
            break
        time.sleep(0.05)
    assert job and job["status"] == "done", job

    published = client.post(
        f"/api/scripts/{started['scriptId']}/publish",
        json={"jobId": started["jobId"]},
        headers={"X-CSRF-Token": "csrf"},
    )
    assert published.status_code == 201, published.get_json()
    assert published.get_json()["data"]["title"] == "Sample"


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
