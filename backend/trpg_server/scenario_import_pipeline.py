"""Deterministic, chunk-oriented scenario import pipeline.

「直接导入」不会把整篇文档交给 LLM，也不会生成可编辑的场景卡。它先按标题把
文档切分为一个个场景/章节块，再逐块嵌入写入向量库；审核模式（AI 转换）仍然
走既有的场景卡生成流程。
"""
from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from trpg_server.scenario_documents import chunk_parsed_document, parse_scenario_document
from trpg_server.scenario_importer import _summary

logger = logging.getLogger(__name__)


def _chunk_title(text: str, index: int) -> str:
    for line in str(text or "").splitlines():
        value = line.strip().lstrip("#").strip()
        if value:
            return value[:120]
    return f"Imported section {index}"


def _local_metadata(chunk: Any, index: int) -> dict[str, Any]:
    title = _chunk_title(getattr(chunk, "text", ""), index)
    lowered = title.casefold()
    if any(word in lowered for word in ("ending", "结局", "true end", "bad end", "crazy end")):
        card_type = "ending"
    elif any(word in lowered for word in ("npc", "人物", "角色", "怪物", "monster")):
        card_type = "npc"
    elif any(word in lowered for word in ("scene", "场景", "地点", "房间", "车厢")):
        card_type = "scene"
    else:
        card_type = "custom"
    return {
        "card_type": card_type,
        "summary": _summary(str(getattr(chunk, "text", "")), 180),
        "title": title,
    }


class ScenarioImportPipeline:
    def __init__(self, store, config=None):
        self.store = store
        self.config = config or {}

    def _cancelled(self, job_id: str) -> bool:
        current = self.store.get(job_id) or {}
        return bool(current.get("cancel_requested"))

    def _update_chunk_progress(self, job_id: str, stage: str, index: int, total: int, start: float, span: float, **extra: Any) -> None:
        ratio = index / max(1, total)
        self.store.update(
            job_id,
            status=stage,
            current_stage=stage,
            progress=round(start + span * ratio, 2),
            stage_progress=round(ratio * 100, 2),
            stage_meta={"totalChunks": total, "processedChunks": index, **extra},
        )

    def run(self, job_id: str, start_stage: str | None = None):
        job = self.store.get(job_id)
        if not job:
            raise ValueError("import job not found")
        source = Path(self.store.root) / job_id / "source" / job["source_filename"]
        try:
            raw = source.read_bytes()
            ocr = self.config.get("OCR_PROVIDER") if self.config.get("OCR_ENABLED") else None
            self.store.update(job_id, status="parsing", current_stage="parsing", progress=5, stage_progress=0)
            parsed = parse_scenario_document(raw, job["source_filename"], ocr_provider=ocr)
            self.store.save_intermediate(job_id, "parsed", {"filename": parsed.filename, "markdown": parsed.markdown, "page_count": parsed.page_count})

            # 直接导入：按标题（Word/PDF 标题、Markdown #、第X章）切分为语义块，
            # 每个标题对应原文中的一个场景/章节，不再生成场景卡。
            sections = chunk_parsed_document(parsed)
            total = len(sections)
            self.store.update(job_id, status="chunking", current_stage="chunking", progress=15, stage_progress=100, stage_meta={"totalChunks": total, "processedChunks": total})
            self.store.save_intermediate(job_id, "chunks", [c.__dict__ for c in sections])

            from trpg_server.agents.embedding_provider import HashedTokenEmbedding
            from trpg_server.agents.knowledge_base import KnowledgeChunk, index_knowledge_chunks

            provider = self.config.get("EMBEDDING_PROVIDER") or HashedTokenEmbedding()
            scenario_id = str(job.get("script_id"))
            scenario_version = str(job.get("target_version") or "1")

            knowledge_chunks: list[KnowledgeChunk] = []
            for index, section in enumerate(sections, 1):
                if self._cancelled(job_id):
                    return self.store.update(job_id, status="cancelled", current_stage="embedding", error="Import cancelled")
                metadata = _local_metadata(section, index)
                chunk = KnowledgeChunk(
                    scenario_id=scenario_id,
                    scenario_version=scenario_version,
                    # 直接导入没有场景卡，块不绑定场景，检索时不被当前场景过滤掉。
                    scene_id=None,
                    card_type=str(metadata.get("card_type") or "custom"),
                    visibility="public",
                    spoiler_level=0,
                    unlock_condition=None,
                    text=section.text,
                    chunk_id=f"chunk-{index:04d}",
                    source_ref={"page": section.page, "page_end": section.page_end, "chapter": section.chapter_path or []},
                    metadata={"title": str(metadata.get("title") or _chunk_title(section.text, index))},
                )
                vectors = provider.embed([chunk.text])
                if not vectors:
                    raise ValueError(f"Embedding returned no vector for chunk {index}")
                knowledge_chunks.append(replace(chunk, embedding=vectors[0]))
                self._update_chunk_progress(job_id, "embedding", index, total, 15, 80)

            index_knowledge_chunks(
                knowledge_chunks,
                vector_store=self.config.get("VECTOR_STORE"),
                embedding_provider=provider,
            )
            self.store.save_intermediate(job_id, "knowledge", [chunk.to_dict() for chunk in knowledge_chunks])

            metadata = job.get("metadata") or {}
            scenario: dict[str, Any] = {
                "id": job.get("script_id"),
                "scenario_version": scenario_version,
                "title": metadata.get("title") or Path(job["source_filename"]).stem,
                "author": metadata.get("author") or "Imported",
                "playerCount": 1,
                "notes": metadata.get("description") or "",
                # 直接导入不生成可编辑场景卡，知识以向量块形式保存。
                "modules": [],
                "import_mode": "direct",
                "conversion": {"version": 4, "source_preserved": True, "document_import": True, "chunk_count": len(knowledge_chunks), "stages": ["parse", "chunk", "embed"]},
            }
            self.store.update(job_id, status="summarizing", current_stage="summarizing", progress=95, stage_progress=100, stage_meta={"totalChunks": total, "processedChunks": total})
            summary = " ".join(str(chunk.text) for chunk in knowledge_chunks)[:1000]
            scenario["global_summary"] = summary
            self.store.save_intermediate(job_id, "preview", scenario)
            logger.info("scenario_import.direct_complete job=%s chunks=%d vectors=%d", job_id, total, len(knowledge_chunks))
            return self.store.update(job_id, status="done", current_stage="done", progress=100, stage_progress=100, stage_meta={"totalChunks": total, "processedChunks": total}, preview=scenario)
        except Exception as exc:
            logger.exception("scenario_import.pipeline_failed job=%s", job_id)
            return self.store.update(job_id, status="failed", error=str(exc), failed_stage=(self.store.get(job_id) or {}).get("current_stage") or "parsing")
