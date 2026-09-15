"""Deterministic local import pipeline used by asynchronous jobs."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from trpg_server.scenario_documents import chunk_parsed_document, parse_scenario_document
from trpg_server.scenario_import_jobs import IMPORT_STAGES
from trpg_server.scenario_importer import convert_script_to_scenario

class ScenarioImportPipeline:
    def __init__(self, store, config=None): self.store, self.config = store, config or {}
    def run(self, job_id: str, start_stage: str | None = None):
        job = self.store.get(job_id)
        if not job: raise ValueError("import job not found")
        source = Path(self.store.root) / job_id / "source" / job["source_filename"]
        try:
            raw = source.read_bytes()
            ocr = self.config.get("OCR_PROVIDER") if self.config.get("OCR_ENABLED") else None
            parsed = parse_scenario_document(raw, job["source_filename"], ocr_provider=ocr)
            self.store.update(job_id, status="parsing", current_stage="parsing", progress=10)
            self.store.save_intermediate(job_id, "parsed", {"filename": parsed.filename, "markdown": parsed.markdown, "page_count": parsed.page_count})
            chunks = chunk_parsed_document(parsed)
            self.store.update(job_id, status="chunking", current_stage="chunking", progress=25, stage_meta={"totalChunks": len(chunks), "processedChunks": len(chunks)})
            self.store.save_intermediate(job_id, "chunks", [c.__dict__ for c in chunks])
            scenario = convert_script_to_scenario(parsed.markdown, {"title": (job.get("metadata") or {}).get("title") or Path(job["source_filename"]).stem, "author": (job.get("metadata") or {}).get("author", "Imported")})
            self.store.update(job_id, status="extracting", current_stage="extracting", progress=50)
            self.store.save_intermediate(job_id, "cards", scenario.get("modules", []))
            self.store.update(job_id, status="summarizing", current_stage="summarizing", progress=75)
            summary = " ".join(str(m.get("summary") or "") for m in scenario.get("modules", []) if isinstance(m, dict)).strip()[:1000]
            scenario["global_summary"] = summary
            self.store.save_intermediate(job_id, "summary", {"global_summary": summary})
            self.store.update(job_id, status="embedding", current_stage="embedding", progress=90)
            from trpg_server.agents.embedding_provider import OpenAICompatibleEmbeddingProvider
            from trpg_server.agents.vector_store import QdrantVectorStore
            texts = [str(item.get("content") or item.get("summary") or "") for item in scenario.get("modules", []) if isinstance(item, dict)]
            provider = self.config.get("EMBEDDING_PROVIDER") or OpenAICompatibleEmbeddingProvider(self.config.get("EMBEDDING_BASE_URL"), self.config.get("EMBEDDING_API_KEY"), self.config.get("EMBEDDING_MODEL"), self.config.get("EMBEDDING_DIMENSIONS", 256))
            vectors = provider.embed(texts) if texts else []
            for module, vector in zip([m for m in scenario.get("modules", []) if isinstance(m, dict)], vectors): module["embedding"] = vector
            if self.config.get("VECTOR_STORE"):
                store = self.config["VECTOR_STORE"]
            else:
                store = QdrantVectorStore(self.config.get("VECTOR_DB_URL"), str(self.config.get("VECTOR_DB_PATH", "data/runtime/vector-db/qdrant")), self.config.get("VECTOR_DB_API_KEY"), self.config.get("EMBEDDING_DIMENSIONS", 256))
            points = [{"id": abs(hash(str(module.get("id")))) % (2**63), "vector": vector, "payload": {"scenario_id": job.get("script_id"), "scenario_version": job.get("target_version"), "module_id": module.get("id")}} for module, vector in zip([m for m in scenario.get("modules", []) if isinstance(m, dict)], vectors)]
            if points: store.upsert(f"scenario_{job.get('script_id')}_{job.get('target_version')}", points)
            self.store.save_intermediate(job_id, "preview", scenario)
            return self.store.update(job_id, status="done", current_stage="done", progress=100, preview=scenario)
        except Exception as exc:
            return self.store.update(job_id, status="failed", error=str(exc), failed_stage=job.get("current_stage") or "parsing")
