"""Deterministic, chunk-oriented scenario import pipeline.

The direct-import path deliberately never sends the entire source document to an
LLM.  It first parses and mechanically chunks the document, then optionally asks
an injected analyzer about one chunk at a time, and finally embeds each chunk
before writing the vector store.  This keeps large imports bounded and makes
progress reporting meaningful.
"""
from __future__ import annotations

import logging
import re
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
        "scene_id": f"scene-{index}" if card_type == "scene" else None,
        "spoiler_level": 1 if card_type in {"scene", "custom"} else 2,
        "visibility": "kp_only" if card_type in {"custom", "npc", "ending"} else "player_visible",
        "unlock_condition": None,
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

    def _analyze_chunk(self, chunk: Any, index: int, total: int) -> dict[str, Any]:
        analyzer = self.config.get("SCENARIO_CHUNK_ANALYZER")
        result: Any = None
        if callable(analyzer):
            try:
                result = analyzer(chunk, index, total)
            except TypeError:
                result = analyzer({"text": chunk.text, "index": index, "total": total})
            except Exception as exc:
                # AI enrichment is optional. A timeout or malformed response
                # for one block must not discard the entire large document;
                # retain deterministic local metadata and continue.
                logger.warning("scenario_import.chunk_ai_fallback index=%s/%s error=%s", index, total, exc)
                result = None
        metadata = _local_metadata(chunk, index)
        if isinstance(result, dict):
            for key in ("card_type", "scene_id", "spoiler_level", "visibility", "unlock_condition", "summary", "title", "attributes", "battle", "triggers", "metadata"):
                if key in result and result[key] is not None:
                    metadata[key] = result[key]
        metadata["card_type"] = str(metadata.get("card_type") or "custom").lower()
        metadata["spoiler_level"] = max(0, min(5, int(metadata.get("spoiler_level") or 0)))
        metadata["visibility"] = str(metadata.get("visibility") or "kp_only")
        return metadata

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

            chunks = chunk_parsed_document(parsed)
            total = len(chunks)
            self.store.update(job_id, status="chunking", current_stage="chunking", progress=15, stage_progress=100, stage_meta={"totalChunks": total, "processedChunks": total})
            self.store.save_intermediate(job_id, "chunks", [c.__dict__ for c in chunks])

            cards: list[dict[str, Any]] = []
            for index, chunk in enumerate(chunks, 1):
                if self._cancelled(job_id):
                    return self.store.update(job_id, status="cancelled", current_stage="extracting", error="Import cancelled")
                metadata = self._analyze_chunk(chunk, index, total)
                module_id = f"{metadata['card_type']}-{index}"
                card = {
                    "id": module_id,
                    "module_id": module_id,
                    "module_type": metadata["card_type"],
                    "card_type": metadata["card_type"],
                    "title": str(metadata.get("title") or _chunk_title(chunk.text, index)),
                    "summary": str(metadata.get("summary") or _summary(chunk.text, 180)),
                    "content": chunk.text,
                    "scene_id": metadata.get("scene_id"),
                    "spoiler_level": metadata["spoiler_level"],
                    "visibility": metadata["visibility"],
                    "unlock_condition": metadata.get("unlock_condition"),
                    "source_order": index,
                    "source_ref": {"page": chunk.page, "page_end": chunk.page_end, "chapter": chunk.chapter_path or []},
                    "metadata": metadata.get("metadata") or {},
                    "attributes": metadata.get("attributes") or {},
                    "battle": metadata.get("battle") or {},
                    "triggers": metadata.get("triggers") or [],
                    "source_preserved": True,
                }
                cards.append(card)
                self._update_chunk_progress(job_id, "extracting", index, total, 15, 45)
                self.store.save_intermediate(job_id, "extractions", cards)

            metadata = job.get("metadata") or {}
            scenario: dict[str, Any] = {
                "id": job.get("script_id"),
                "scenario_version": str(job.get("target_version") or "1"),
                "title": metadata.get("title") or Path(job["source_filename"]).stem,
                "author": metadata.get("author") or "Imported",
                "playerCount": 1,
                "notes": metadata.get("description") or "",
                "modules": cards,
                "import_mode": "direct",
                "conversion": {"version": 4, "source_preserved": True, "module_count": len(cards), "stages": ["parse", "chunk", "extract", "embed"]},
            }
            self.store.update(job_id, status="carding", current_stage="carding", progress=65, stage_progress=100, stage_meta={"totalChunks": total, "processedChunks": total, "totalCards": len(cards), "processedCards": len(cards)})
            summary = " ".join(str(card.get("summary") or "") for card in cards)[:1000]
            scenario["global_summary"] = summary
            self.store.save_intermediate(job_id, "cards", cards)
            self.store.save_intermediate(job_id, "summary", {"global_summary": summary})

            from trpg_server.agents.embedding_provider import HashedTokenEmbedding
            from trpg_server.agents.knowledge_base import build_knowledge_chunks, index_knowledge_chunks

            provider = self.config.get("EMBEDDING_PROVIDER") or HashedTokenEmbedding()
            for index, card in enumerate(cards, 1):
                if self._cancelled(job_id):
                    return self.store.update(job_id, status="cancelled", current_stage="embedding", error="Import cancelled")
                vectors = provider.embed([str(card.get("content") or "")])
                if not vectors:
                    raise ValueError(f"Embedding returned no vector for chunk {index}")
                card["embedding"] = vectors[0]
                self._update_chunk_progress(job_id, "embedding", index, total, 65, 33)

            index_knowledge_chunks(
                build_knowledge_chunks(scenario),
                vector_store=self.config.get("VECTOR_STORE"),
                embedding_provider=provider,
            )
            self.store.save_intermediate(job_id, "preview", scenario)
            logger.info("scenario_import.direct_complete job=%s chunks=%d vectors=%d", job_id, total, len(cards))
            return self.store.update(job_id, status="done", current_stage="done", progress=100, stage_progress=100, stage_meta={"totalChunks": total, "processedChunks": total, "totalCards": len(cards), "processedCards": len(cards)}, preview=scenario)
        except Exception as exc:
            logger.exception("scenario_import.pipeline_failed job=%s", job_id)
            return self.store.update(job_id, status="failed", error=str(exc), failed_stage=(self.store.get(job_id) or {}).get("current_stage") or "parsing")
