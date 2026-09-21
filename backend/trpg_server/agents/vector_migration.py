"""Migrate human-readable scenario JSON indexes into a vector store."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trpg_server.agents.embedding_provider import HashedTokenEmbedding
from trpg_server.agents.knowledge_base import KnowledgeChunk, index_knowledge_chunks
from trpg_server.json_store import read_json


def migrate_json_indexes(scenarios_dir: str | Path, vector_store: Any, embedding_provider: Any = None) -> dict[str, int]:
    root = Path(scenarios_dir)
    provider = embedding_provider or HashedTokenEmbedding()
    files = 0
    chunks = 0
    skipped = 0
    for path in sorted(root.glob("scenario-*/knowledge-index/*.json")):
        values = read_json(path, default=[])
        if not isinstance(values, list):
            skipped += 1
            continue
        parsed: list[KnowledgeChunk] = []
        for value in values:
            if not isinstance(value, dict):
                skipped += 1
                continue
            try:
                parsed.append(KnowledgeChunk(**value))
            except TypeError:
                skipped += 1
        if not parsed:
            continue
        index_knowledge_chunks(parsed, vector_store=vector_store, embedding_provider=provider)
        files += 1
        chunks += len(parsed)
    return {"files": files, "chunks": chunks, "skipped": skipped}


def migrate_qdrant_store(source: Any, vector_store: Any) -> dict[str, int]:
    """Copy all readable Qdrant points into the embedded store without deleting them."""
    client = getattr(source, "client", source)
    if client is None:
        raise RuntimeError("qdrant-client is not installed or the source is unavailable")
    files = 0
    chunks = 0
    for descriptor in client.get_collections().collections:
        collection = str(descriptor.name)
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            records = []
            for point in points:
                vector = getattr(point, "vector", None)
                payload = dict(getattr(point, "payload", None) or {})
                if not isinstance(vector, list):
                    continue
                payload.setdefault("collection", collection)
                payload.setdefault("chunk_id", payload.get("module_id") or str(getattr(point, "id", "")))
                records.append({**payload, "id": payload["chunk_id"], "embedding": vector})
            if records:
                vector_store.upsert(records)
                chunks += len(records)
            if not offset or not points:
                break
        files += 1
    return {"collections": files, "chunks": chunks}
