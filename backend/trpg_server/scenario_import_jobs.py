"""Persistent import job state and a small in-process executor."""
from __future__ import annotations
import json, secrets, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping
from trpg_server.json_store import read_json, write_json_atomic

IMPORT_STAGES = ("parsing", "chunking", "extracting", "merging", "carding", "summarizing", "embedding")
TERMINAL = {"done", "failed", "cancelled", "published"}

class ImportJobStore:
    def __init__(self, root: Path):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True); self._lock = threading.RLock()
    def _path(self, job_id: str) -> Path: return self.root / str(job_id) / "job.json"
    def create(self, *, owner_id: str, filename: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
        now = time.time(); job_id = secrets.token_urlsafe(18)
        job = {"id": job_id, "owner_id": str(owner_id), "script_id": int(now * 1000), "target_version": "1", "source_filename": filename, "metadata": dict(metadata), "status": "pending", "progress": 0, "current_stage": "pending", "stage_progress": 0, "stage_meta": {}, "intermediate_results": {}, "cancel_requested": False, "retry_count": 0, "created_at": now, "updated_at": now}
        self.update(job_id, **job); return job
    def get(self, job_id: str) -> dict[str, Any] | None: return read_json(self._path(job_id), default=None)
    def update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            current = self.get(job_id) or {"id": job_id}
            current.update(changes); current["updated_at"] = time.time(); write_json_atomic(self._path(job_id), current); return current
    def save_intermediate(self, job_id: str, name: str, value: Any) -> Path:
        path = self.root / str(job_id) / "intermediate" / f"{name}.json"; write_json_atomic(path, value); self.update(job_id, intermediate_results={**(self.get(job_id) or {}).get("intermediate_results", {}), name: str(path.relative_to(self.root / str(job_id)))}); return path
    def load_intermediate(self, job_id: str, name: str, default: Any = None) -> Any:
        job = self.get(job_id) or {}; rel = (job.get("intermediate_results") or {}).get(name, f"intermediate/{name}.json"); return read_json(self.root / str(job_id) / rel, default=default)
    def request_cancel(self, job_id: str) -> dict[str, Any]: return self.update(job_id, cancel_requested=True)
    def recover_interrupted(self) -> int:
        count = 0
        for path in self.root.glob("*/job.json"):
            job = read_json(path, default={})
            if job.get("status") not in TERMINAL and job.get("status") != "pending": self.update(job["id"], status="failed", error="worker interrupted", failed_stage=job.get("current_stage")); count += 1
        return count

def public_job_payload(job: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(job); value.pop("embedding", None); value.pop("intermediate_results", None); return value

def submit_import_job(app, job_id: str, start_stage: str | None = None):
    executor = app.extensions["scenario_import_executor"]
    def runner():
        with app.app_context():
            from trpg_server.scenario_import_pipeline import ScenarioImportPipeline
            ScenarioImportPipeline(app.extensions["scenario_import_store"], app.config).run(job_id, start_stage=start_stage)
    return executor.submit(runner)
