"""Scenario knowledge cards and safe room-scoped retrieval.

The default implementation intentionally uses a deterministic lexical scorer so the
server remains dependency-free. A vector backend can implement the same card
contract later without changing callers.
"""

from __future__ import annotations

import re
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.scenario_store import load_scenario_by_id


@dataclass(frozen=True)
class KnowledgeChunk:
    scenario_id: str
    scenario_version: str
    scene_id: str | None
    card_type: str
    visibility: str
    spoiler_level: int
    unlock_condition: str | None
    text: str
    chunk_id: str
    embedding: list[float] | None = None
    source_ref: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    attachments: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _version(data: Mapping[str, Any], *keys: str, default: str = "1") -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _iter_modules(scenario: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    modules = scenario.get("modules")
    if isinstance(modules, list) and modules:
        yield from (item for item in modules if isinstance(item, dict))
        return
    for collection, card_type in (("scenes", "scene"), ("endings", "ending")):
        values = scenario.get(collection)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict):
                    yield {**item, "module_type": item.get("module_type") or card_type}


def build_knowledge_chunks(scenario: Mapping[str, Any] | None) -> list[KnowledgeChunk]:
    """Convert a normalized scenario into versioned, filterable cards."""
    if not isinstance(scenario, Mapping):
        return []
    scenario_id = str(scenario.get("id") or scenario.get("scenario_id") or "unknown")
    scenario_version = _version(scenario, "scenario_version", "version", "version_id")
    chunks: list[KnowledgeChunk] = []
    for index, module in enumerate(_iter_modules(scenario), 1):
        text = str(module.get("content") or module.get("text") or module.get("summary") or "").strip()
        if not text:
            continue
        card_type = str(module.get("card_type") or module.get("module_type") or "custom").strip().lower()
        scene_id = module.get("scene_id")
        if scene_id in (None, "") and card_type in {"scene", "ending"}:
            scene_id = module.get("id")
        chunk_id = str(module.get("chunk_id") or module.get("id") or f"{card_type}-{index}")
        chunks.append(
            KnowledgeChunk(
                scenario_id=scenario_id,
                scenario_version=_version(module, "scenario_version", default=scenario_version),
                scene_id=str(scene_id) if scene_id not in (None, "") else None,
                card_type=card_type,
                visibility=str(module.get("visibility") or "player_visible"),
                spoiler_level=max(0, _int(module.get("spoiler_level"), 0)),
                unlock_condition=(str(module.get("unlock_condition")) if module.get("unlock_condition") else None),
                text=text,
                chunk_id=chunk_id,
                embedding=module.get("embedding") if isinstance(module.get("embedding"), list) else None,
                source_ref=module.get("source_ref") if isinstance(module.get("source_ref"), dict) else None,
                metadata=module.get("metadata") if isinstance(module.get("metadata"), dict) else None,
                attachments=module.get("attachments") if isinstance(module.get("attachments"), list) else None,
            )
        )
    return chunks


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[\w\u4e00-\u9fff]+", value.casefold()) if token]


class KnowledgeBaseService:
    """Room-aware retrieval facade; callers never access the index directly."""

    def __init__(
        self,
        rooms_dir: Path | None = None,
        scenarios_dir: Path | None = None,
        scenarios: Mapping[str, Mapping[str, Any]] | None = None,
        vector_store: Any = None,
        embedding_provider: Any = None,
    ):
        self.rooms_dir = Path(rooms_dir) if rooms_dir else None
        self.scenarios_dir = Path(scenarios_dir) if scenarios_dir else None
        self.scenarios = {str(key): dict(value) for key, value in (scenarios or {}).items()}
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self._chunks: dict[tuple[str, str], list[KnowledgeChunk]] = {}

    def _room_info(self, room_id: str) -> dict[str, Any]:
        if not self.rooms_dir:
            return {}
        return read_json(self.rooms_dir / str(room_id) / "info.json", default={})

    def _scenario(self, scenario_id: Any, scenario_version: Any = None) -> dict[str, Any] | None:
        if scenario_id in (None, ""):
            return None
        scenario = self.scenarios.get(str(scenario_id))
        if scenario is not None:
            return scenario
        if self.scenarios_dir:
            path, scenario = load_scenario_by_id(self.scenarios_dir, scenario_id, scenario_version=scenario_version)
            if scenario and path:
                scenario = dict(scenario)
                scenario["__descriptor_path"] = str(path)
            return scenario
        return None

    def _get_chunks(self, scenario: Mapping[str, Any]) -> list[KnowledgeChunk]:
        key = (str(scenario.get("id")), _version(scenario, "scenario_version", "version", "version_id"))
        if key not in self._chunks:
            source = scenario.get("__descriptor_path")
            loaded = load_knowledge_index(Path(str(source)), key[1]) if source else []
            self._chunks[key] = loaded or build_knowledge_chunks(scenario)
        return self._chunks[key]

    def search(self, room_id: str, query: str, top_k: int = 5, audience: str = "kp") -> list[dict[str, Any]]:
        info = self._room_info(room_id)
        scenario = self._scenario(info.get("scenario_id"), info.get("scenario_version"))
        if not scenario:
            return []
        scenario_id = str(scenario.get("id") or info.get("scenario_id"))
        scenario_version = str(info.get("scenario_version") or _version(scenario, "scenario_version", "version", "version_id"))
        current_scene = str(info.get("active_scene_id") or info.get("current_scene_id") or "") or None
        spoiler_level = max(0, _int(info.get("spoiler_level") or info.get("current_spoiler_level"), 0))
        query_tokens = _tokens(str(query or ""))
        filtered: list[KnowledgeChunk] = []
        for chunk in self._get_chunks(scenario):
            if chunk.scenario_id != scenario_id or chunk.scenario_version != scenario_version:
                continue
            if chunk.scene_id not in (None, current_scene):
                continue
            if chunk.spoiler_level > spoiler_level:
                continue
            if audience != "kp" and chunk.visibility == "kp_only":
                continue
            filtered.append(chunk)

        vector_scores: dict[str, float] = {}
        query_vector: list[float] | None = None
        if query and self.embedding_provider is not None:
            try:
                embedded = self.embedding_provider.embed([str(query)])
                query_vector = embedded[0] if embedded else None
            except Exception:
                query_vector = None
        if query_vector and self.vector_store is not None:
            try:
                collection = f"scenario_{scenario_id}_{scenario_version}"
                query_store = getattr(self.vector_store, "query", None)
                if callable(query_store):
                    try:
                        vector_results = query_store(
                            query_vector,
                            {
                                "collection": collection,
                                "scenario_id": scenario_id,
                                "scenario_version": scenario_version,
                            },
                            max(20, int(top_k) * 4),
                        )
                    except NotImplementedError:
                        vector_results = self.vector_store.search(collection, query_vector, limit=max(20, int(top_k) * 4))
                else:
                    vector_results = self.vector_store.search(collection, query_vector, limit=max(20, int(top_k) * 4))
                allowed_ids = {chunk.chunk_id for chunk in filtered}
                for item in vector_results:
                    payload = item.get("payload") if isinstance(item, dict) else {}
                    payload = payload if isinstance(payload, dict) else {}
                    chunk_id = str(payload.get("chunk_id") or payload.get("module_id") or item.get("id") or "")
                    if chunk_id in allowed_ids:
                        vector_scores[chunk_id] = max(vector_scores.get(chunk_id, 0.0), float(item.get("score") or 0.0))
            except Exception:
                vector_scores = {}

        candidates: list[tuple[float, KnowledgeChunk, float, float]] = []
        for chunk in filtered:
            haystack = _tokens(f"{chunk.text} {chunk.card_type} {chunk.unlock_condition or ''}")
            lexical = float(sum(haystack.count(token) for token in query_tokens) if query_tokens else 1)
            vector = vector_scores.get(chunk.chunk_id, 0.0)
            if not vector and chunk.embedding:
                qv = query_vector if query_vector and len(query_vector) == len(chunk.embedding) else [0.0] * len(chunk.embedding)
                for token in query_tokens:
                    if query_vector is None:
                        qv[hash(token) % len(qv)] += 1.0
                norm = math.sqrt(sum(v * v for v in qv)) or 1.0
                cnorm = math.sqrt(sum(v * v for v in chunk.embedding)) or 1.0
                vector = sum(a * b for a, b in zip(qv, chunk.embedding)) / (norm * cnorm)
            score = lexical + vector
            if score <= 0:
                continue
            candidates.append((score, chunk, lexical, vector))
        candidates.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            {**chunk.to_dict(), "score": score, "score_components": {"lexical": lexical, "vector": vector}}
            for score, chunk, lexical, vector in candidates[: max(1, min(int(top_k), 20))]
        ]


def search(
    room_id: str,
    query: str,
    *,
    rooms_dir: Path | None = None,
    scenarios_dir: Path | None = None,
    top_k: int = 5,
    audience: str = "kp",
) -> list[dict[str, Any]]:
    """Functional facade kept for API callers that do not need a long-lived service."""
    return KnowledgeBaseService(rooms_dir=rooms_dir, scenarios_dir=scenarios_dir).search(
        room_id, query, top_k=top_k, audience=audience
    )


def knowledge_index_path(descriptor_path: Path, version: Any) -> Path:
    base = descriptor_path.parent.parent if descriptor_path.parent.name == "versions" else descriptor_path.parent
    return base / "knowledge-index" / f"{version}.json"


def index_knowledge_chunks(
    chunks: Iterable[KnowledgeChunk],
    *,
    vector_store: Any = None,
    embedding_provider: Any = None,
) -> list[KnowledgeChunk]:
    """Fill missing embeddings and idempotently write chunks to a vector store."""
    prepared = list(chunks)
    missing = [index for index, chunk in enumerate(prepared) if not chunk.embedding]
    if missing and embedding_provider is not None:
        try:
            vectors = embedding_provider.embed([prepared[index].text for index in missing])
        except Exception:
            vectors = []
        for index, vector in zip(missing, vectors):
            if isinstance(vector, list) and vector:
                prepared[index] = replace(prepared[index], embedding=[float(value) for value in vector])
    if vector_store is not None:
        records = []
        for chunk in prepared:
            if not chunk.embedding:
                continue
            record = chunk.to_dict()
            record["collection"] = f"scenario_{chunk.scenario_id}_{chunk.scenario_version}"
            records.append(record)
        if records:
            vector_store.upsert(records)
    return prepared


def persist_knowledge_index(
    descriptor_path: Path,
    scenario: Mapping[str, Any],
    *,
    vector_store: Any = None,
    embedding_provider: Any = None,
) -> Path:
    version = _version(scenario, "scenario_version", "version", "version_id")
    path = knowledge_index_path(descriptor_path, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = index_knowledge_chunks(
        build_knowledge_chunks(scenario),
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )
    write_json_atomic(path, [chunk.to_dict() for chunk in chunks])
    return path


def load_knowledge_index(descriptor_path: Path, version: Any) -> list[KnowledgeChunk]:
    path = knowledge_index_path(descriptor_path, version)
    if not path.exists() and str(version).isdigit():
        from trpg_server.agents.versioning import normalize_semver
        path = knowledge_index_path(descriptor_path, normalize_semver(version))
    values = read_json(path, default=[])
    if not isinstance(values, list):
        return []
    result = []
    for item in values:
        if not isinstance(item, dict):
            continue
        try:
            result.append(KnowledgeChunk(**item))
        except TypeError:
            continue
    return result
