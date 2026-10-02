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


def lexical_match_score(haystack: str, query: str) -> float:
    """Deterministic lexical score shared by scenario and ruleset retrieval.

    Latin tokens are matched as whole words, but CJK text cannot be split on
    whitespace: tokenising ``走进图书馆`` as a single run means an exact token
    comparison never matches a query such as ``图书馆``. Overlapping character
    bigrams let a CJK query match an occurrence inside a longer run while
    keeping the scorer dependency-free.
    """
    hay = str(haystack or "").casefold()
    query_tokens = _tokens(query)
    if not query_tokens:
        return 1.0
    score = 0.0
    for token in query_tokens:
        if token.isascii() or len(token) < 2:
            score += hay.count(token)
            continue
        score += sum(hay.count(token[index : index + 2]) for index in range(len(token) - 1))
    return score


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")

# 规则类查询更依赖精确词形（技能名/属性名/规则术语），叙事类查询更依赖语义向量。
_RULE_QUERY_HINTS = (
    "检定", "规则", "技能", "伤害", "骰", "属性", "成功", "失败",
    "check", "rule", "skill", "damage", "dice",
)


def _bm25_tokens(value: str) -> list[str]:
    """BM25 分词：拉丁词整词，CJK 拆成二元组（中文无法用空格切分）。"""
    tokens: list[str] = []
    for token in _TOKEN_PATTERN.findall(str(value or "").casefold()):
        if token[0].isascii() or len(token) == 1:
            tokens.append(token)
        else:
            tokens.extend(token[index:index + 2] for index in range(len(token) - 1))
    return tokens


def _bm25_scores(texts: list[str], query_tokens: list[str]) -> list[float]:
    """在当前语料（硬过滤后的知识块）上计算 DF 得到 IDF，返回每个文档的词法分。

    IDF 在子集上计算，冷门词（专有人名/地名）能拿到更高权重；泛化输入与所有
    文档都无交集时整体趋近 0，从而自然落到兜底路径。
    """
    corpus = [_bm25_tokens(text) for text in texts]
    total = len(corpus)
    document_frequency: dict[str, int] = {}
    for tokens in corpus:
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    average_length = sum(len(tokens) for tokens in corpus) / max(1, total)
    k1, b = 1.5, 0.75
    scores: list[float] = []
    for tokens in corpus:
        length = len(tokens) or 1
        frequency: dict[str, int] = {}
        for token in tokens:
            frequency[token] = frequency.get(token, 0) + 1
        score = 0.0
        for query_token in set(query_tokens):
            term_frequency = frequency.get(query_token, 0)
            if not term_frequency:
                continue
            idf = math.log(1 + (total + 1) / (document_frequency.get(query_token, 0) + 1))
            score += idf * (term_frequency * (k1 + 1)) / (
                term_frequency + k1 * (1 - b + b * length / average_length)
            )
        scores.append(score)
    return scores


def _normalize_scores(scores: list[float]) -> list[float]:
    """把一组分数线性归一化到 [0, 1]（全 0 时保持全 0）。"""
    top = max(scores) if scores else 0.0
    if top <= 0:
        return [0.0 for _ in scores]
    return [score / top for score in scores]


def _score_weights(query: str) -> tuple[float, float]:
    """按查询类型给出 (词法权重, 向量权重)：规则类问题偏词法，叙事类偏向量。"""
    text = str(query or "").casefold()
    if any(hint in text for hint in _RULE_QUERY_HINTS):
        return 1.0, 0.6
    return 0.75, 1.0


def _section_key(chunk: KnowledgeChunk) -> str:
    """章节级去重键：同一章节的多个子块取值相同，无章节信息时退化为 chunk_id。"""
    metadata = chunk.metadata if isinstance(chunk.metadata, dict) else {}
    section = str(metadata.get("section") or "").strip()
    return f"section:{section}" if section else chunk.chunk_id


def _merge_section_text(
    chunks: list[KnowledgeChunk], hit: KnowledgeChunk, parent_max_chars: int
) -> tuple[str, list[str]]:
    """从命中子块向两侧回填同章节的相邻块，拼成完整章节（受父块上限约束）。"""
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    try:
        index = chunk_ids.index(hit.chunk_id)
    except ValueError:
        return hit.text, [hit.chunk_id]
    pieces = [chunks[index].text]
    total = len(pieces[0])
    left = right = index
    while True:
        extended = False
        if right + 1 < len(chunks) and total + len(chunks[right + 1].text) <= parent_max_chars:
            right += 1
            pieces.append(chunks[right].text)
            total += len(chunks[right].text)
            extended = True
        if left - 1 >= 0 and total + len(chunks[left - 1].text) <= parent_max_chars:
            left -= 1
            pieces.insert(0, chunks[left].text)
            total += len(chunks[left].text)
            extended = True
        if not extended:
            break
    metadata = hit.metadata if isinstance(hit.metadata, dict) else {}
    marker = str(metadata.get("section") or "").strip()
    cleaned: list[str] = []
    for offset, piece in enumerate(pieces):
        # 续块带「【章节】」前缀，合并时只保留一次，避免重复噪声。
        if offset and marker:
            prefix = f"【{marker}】"
            if piece.startswith(prefix):
                piece = piece[len(prefix):].lstrip("\n")
        cleaned.append(piece)
    return "\n".join(cleaned).strip(), chunk_ids[left:right + 1]


def _grouped_result(
    chunk: KnowledgeChunk, merged_text: str, chunk_ids: list[str], score: float, lexical: float, vector: float
) -> dict[str, Any]:
    result = chunk.to_dict()
    result["text"] = merged_text
    result["chunk_ids"] = chunk_ids
    result["score"] = score
    result["score_components"] = {"lexical": lexical, "vector": vector}
    return result


@dataclass(frozen=True)
class _ScoredChunk:
    """一个候选块的检索结果（score 为归一化加权分，lexical/vector 为原始分）。"""

    chunk: KnowledgeChunk
    score: float
    lexical: float
    vector: float


def _group_by_section(chunks: list[KnowledgeChunk]) -> dict[str, list[KnowledgeChunk]]:
    """按章节归组，保持块在剧本文档中的原始顺序（回填时依赖该顺序）。"""
    sections: dict[str, list[KnowledgeChunk]] = {}
    for chunk in chunks:
        sections.setdefault(_section_key(chunk), []).append(chunk)
    return sections


def _sticky_cooldown_keys(
    recent_rounds: list[list[str]], sticky_rounds: int, cooldown_rounds: int
) -> tuple[set[str], set[str]]:
    """从最近若干轮召回历史中拆出「粘滞（加权）」与「冷却（降权）」章节集合。"""
    sticky: set[str] = set()
    if sticky_rounds > 0:
        for round_keys in recent_rounds[-sticky_rounds:]:
            sticky.update(round_keys)
    cooldown: set[str] = set()
    if cooldown_rounds > 0:
        for round_keys in recent_rounds[-cooldown_rounds:]:
            cooldown.update(round_keys)
    return sticky, cooldown


def _rank_sections(
    scored: list[_ScoredChunk], sticky_keys: set[str], cooldown_keys: set[str], limit: int
) -> list[tuple[str, _ScoredChunk]]:
    """每章只保留得分最高的子块作为命中点，再按「得分 + 粘滞/冷却偏置」排序。

    偏置只影响排序，不改变命中集合，也不截断内容。
    """
    best: dict[str, _ScoredChunk] = {}
    for item in scored:
        key = _section_key(item.chunk)
        current = best.get(key)
        if current is None or item.score > current.score:
            best[key] = item

    def bias(key: str) -> float:
        value = 0.0
        if key in sticky_keys:
            value += 0.15
        if key in cooldown_keys:
            value -= 0.20
        return value

    return sorted(best.items(), key=lambda item: (-(item[1].score + bias(item[0])), item[0]))[:limit]


def _fallback_ranked(
    chunks: list[KnowledgeChunk], cooldown_keys: set[str], limit: int
) -> list[tuple[str, KnowledgeChunk]]:
    """未命中时的兜底排序：优先返回冷却之外的章节，使召回随剧情推进而前进。

    直接导入的剧本没有场景模块，内容仅在知识块中，返回空会让模型「忘记」剧本，
    因此词法与向量均未命中时仍必须给出内容。
    """
    ordered = [chunk for chunk in chunks if _section_key(chunk) not in cooldown_keys] or chunks
    picked: dict[str, KnowledgeChunk] = {}
    for chunk in ordered:
        picked.setdefault(_section_key(chunk), chunk)
        if len(picked) >= limit:
            break
    return list(picked.items())


def _render_section(hit: _ScoredChunk, sections: dict[str, list[KnowledgeChunk]], parent_max_chars: int) -> dict[str, Any]:
    """把命中的子块回填成一条完整章节结果。"""
    chunk = hit.chunk
    merged_text, chunk_ids = _merge_section_text(sections.get(_section_key(chunk), [chunk]), chunk, parent_max_chars)
    return _grouped_result(chunk, merged_text, chunk_ids, hit.score, hit.lexical, hit.vector)


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
        room_dir = self.rooms_dir / str(room_id)
        info = read_json(room_dir / "info.json", default={})
        state = read_json(room_dir / "state.json", default={})
        if isinstance(info, dict) and isinstance(state, dict) and state.get("active_scene_id") not in (None, ""):
            info = {**info, "active_scene_id": state["active_scene_id"]}
        return info

    def _cursor_path(self, room_id: str) -> Path | None:
        if not self.rooms_dir:
            return None
        return self.rooms_dir / str(room_id) / "knowledge_cursor.json"

    @staticmethod
    def _cursor_key(scenario_id: Any, scenario_version: Any) -> str:
        return f"{scenario_id}@{scenario_version}"

    def _recent_rounds(self, room_id: str, scenario_key: str, rounds: int) -> list[list[str]]:
        """本房间最近若干轮召回过的章节 key，用于章节粘滞/冷却排序。

        游标绑定剧本身份：房间换绑/升级剧本后 chunk_id 会重新从 ``chunk-0001``
        开始，旧游标若不失效，新剧本的块会被误判为「已消费」。
        """
        path = self._cursor_path(room_id)
        if path is None:
            return []
        data = read_json(path, default={})
        if not isinstance(data, dict) or str(data.get("scenario") or "") != scenario_key:
            return []
        history = data.get("rounds")
        if not isinstance(history, list):
            return []
        result: list[list[str]] = []
        for item in history:
            if isinstance(item, list):
                result.append([str(value) for value in item if str(value).strip()])
        return result[-max(1, rounds):]

    def _remember_round(self, room_id: str, keys: Iterable[str], scenario_key: str, keep: int) -> None:
        """把本轮召回的章节 key 追加为一条 round（按剧本身份隔离）。"""
        path = self._cursor_path(room_id)
        if path is None:
            return
        data = read_json(path, default={})
        previous = data.get("rounds") if isinstance(data, dict) else None
        rounds: list[list[str]] = []
        if isinstance(previous, list):
            for item in previous:
                if isinstance(item, list):
                    rounds.append([str(value) for value in item if str(value).strip()])
        rounds.append([str(key) for key in keys if str(key).strip()])
        write_json_atomic(path, {"scenario": scenario_key, "rounds": rounds[-max(1, keep):]})

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

    def _eligible_chunks(
        self,
        scenario: Mapping[str, Any],
        scenario_id: str,
        scenario_version: str,
        current_scene: str | None,
        spoiler_level: int,
        audience: str,
    ) -> list[KnowledgeChunk]:
        """筛出本房间当前可检索的块：版本匹配、场景未切出、未剧透、可见性允许。"""
        eligible: list[KnowledgeChunk] = []
        for chunk in self._get_chunks(scenario):
            if chunk.scenario_id != scenario_id or chunk.scenario_version != scenario_version:
                continue
            if chunk.scene_id not in (None, current_scene):
                continue
            if chunk.spoiler_level > spoiler_level:
                continue
            if audience != "kp" and chunk.visibility == "kp_only":
                continue
            eligible.append(chunk)
        return eligible

    def _vector_score_map(
        self, query: str, scenario_id: str, scenario_version: str, chunks: list[KnowledgeChunk], top_k: int
    ) -> dict[str, float]:
        """chunk_id → 向量相似度；向量库不可用时退回块自带 embedding 的本地余弦。"""
        store_scores: dict[str, float] = {}
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
                allowed_ids = {chunk.chunk_id for chunk in chunks}
                for item in vector_results:
                    payload = item.get("payload") if isinstance(item, dict) else {}
                    payload = payload if isinstance(payload, dict) else {}
                    chunk_id = str(payload.get("chunk_id") or payload.get("module_id") or item.get("id") or "")
                    if chunk_id in allowed_ids:
                        store_scores[chunk_id] = max(store_scores.get(chunk_id, 0.0), float(item.get("score") or 0.0))
            except Exception:
                store_scores = {}

        query_tokens = _tokens(str(query or ""))
        scores: dict[str, float] = {}
        for chunk in chunks:
            score = store_scores.get(chunk.chunk_id, 0.0)
            if not score and chunk.embedding:
                qv = query_vector if query_vector and len(query_vector) == len(chunk.embedding) else [0.0] * len(chunk.embedding)
                if query_vector is None:
                    for token in query_tokens:
                        qv[hash(token) % len(qv)] += 1.0
                norm = math.sqrt(sum(value * value for value in qv)) or 1.0
                cnorm = math.sqrt(sum(value * value for value in chunk.embedding)) or 1.0
                score = sum(a * b for a, b in zip(qv, chunk.embedding)) / (norm * cnorm)
            scores[chunk.chunk_id] = score
        return scores

    def _score_chunks(
        self, chunks: list[KnowledgeChunk], query: str, scenario_id: str, scenario_version: str, top_k: int
    ) -> list[_ScoredChunk]:
        """词法 BM25 分与向量分各自归一化后按查询类型加权，得到候选块打分。

        ``_ScoredChunk.lexical``/``vector`` 保留原始分（供调用方观察），``score``
        是归一化加权后的排序分。
        """
        vector_scores = self._vector_score_map(query, scenario_id, scenario_version, chunks, top_k)
        lexical_values = _bm25_scores(
            [f"{chunk.text} {chunk.card_type} {chunk.unlock_condition or ''}" for chunk in chunks],
            _bm25_tokens(str(query or "")),
        )
        lexical_weight, vector_weight = _score_weights(query)
        lexical_norm = _normalize_scores(list(lexical_values))
        vector_norm = _normalize_scores([vector_scores.get(chunk.chunk_id, 0.0) for chunk in chunks])
        scored: list[_ScoredChunk] = []
        for index, chunk in enumerate(chunks):
            score = lexical_weight * lexical_norm[index] + vector_weight * vector_norm[index]
            if score <= 0:
                continue
            scored.append(
                _ScoredChunk(
                    chunk=chunk,
                    score=score,
                    lexical=lexical_values[index],
                    vector=vector_scores.get(chunk.chunk_id, 0.0),
                )
            )
        return scored

    def catalog(self, room_id: str, limit: int = 200) -> list[dict[str, Any]]:
        """返回房间绑定剧本的章节目录（标题/类型/ID）。

        直接导入的剧本没有 scene_manifest，模型缺少整体结构索引；这里按知识块
        顺序给出目录，让模型像普通剧本一样"知道"有哪些章节，再靠每轮注入的
        检索结果读取原文。
        """
        info = self._room_info(room_id)
        scenario = self._scenario(info.get("scenario_id"), info.get("scenario_version"))
        if not scenario:
            return []
        scenario_id = str(scenario.get("id") or info.get("scenario_id"))
        scenario_version = str(info.get("scenario_version") or _version(scenario, "scenario_version", "version", "version_id"))
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for chunk in self._get_chunks(scenario):
            if chunk.scenario_id != scenario_id or chunk.scenario_version != scenario_version:
                continue
            # 同一章节可能被拆成多个子块，目录按章节去重，避免重复标题撑大系统提示。
            key = _section_key(chunk)
            if key in seen:
                continue
            seen.add(key)
            metadata = chunk.metadata if isinstance(chunk.metadata, dict) else {}
            title = str(metadata.get("title") or "").strip() or chunk.chunk_id
            entries.append({"chunk_id": chunk.chunk_id, "title": title, "card_type": chunk.card_type})
            if len(entries) >= limit:
                break
        return entries

    def search(
        self,
        room_id: str,
        query: str,
        top_k: int = 5,
        audience: str = "kp",
        sticky_rounds: int = 1,
        cooldown_rounds: int = 3,
        parent_max_chars: int = 2400,
    ) -> list[dict[str, Any]]:
        info = self._room_info(room_id)
        scenario = self._scenario(info.get("scenario_id"), info.get("scenario_version"))
        if not scenario:
            return []
        scenario_id = str(scenario.get("id") or info.get("scenario_id"))
        scenario_version = str(info.get("scenario_version") or _version(scenario, "scenario_version", "version", "version_id"))
        current_scene = str(info.get("active_scene_id") or info.get("current_scene_id") or "") or None
        spoiler_level = max(0, _int(info.get("spoiler_level") or info.get("current_spoiler_level"), 0))
        filtered = self._eligible_chunks(
            scenario, scenario_id, scenario_version, current_scene, spoiler_level, audience
        )
        if not filtered:
            return []
        scored = self._score_chunks(filtered, str(query or ""), scenario_id, scenario_version, int(top_k))
        sections = _group_by_section(filtered)

        scenario_key = self._cursor_key(scenario_id, scenario_version)
        keep = max(1, sticky_rounds, cooldown_rounds)
        recent_rounds = self._recent_rounds(room_id, scenario_key, keep)
        sticky_keys, cooldown_keys = _sticky_cooldown_keys(recent_rounds, sticky_rounds, cooldown_rounds)
        limit = max(1, min(int(top_k), 20))

        if scored:
            ranked = _rank_sections(scored, sticky_keys, cooldown_keys, limit)
            results = [_render_section(hit, sections, parent_max_chars) for _key, hit in ranked]
            keys = [key for key, _hit in ranked]
        else:
            picked = _fallback_ranked(filtered, cooldown_keys, limit)
            results = [
                _render_section(_ScoredChunk(chunk=chunk, score=0.0, lexical=0.0, vector=0.0), sections, parent_max_chars)
                for _key, chunk in picked
            ]
            keys = [key for key, _chunk in picked]
        self._remember_round(room_id, keys, scenario_key, keep)
        return results


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


def write_knowledge_index(descriptor_path: Path, version: Any, chunks: Iterable[KnowledgeChunk]) -> Path:
    """直接写入已有的知识块（用于「直接导入」文档时跳过场景卡的情形）。

    ``persist_knowledge_index`` 只能从场景的 ``modules`` 构建分块；直接导入的
    剧本没有场景卡，因此需要把切分并嵌入后的知识块直接落盘。
    """
    path = knowledge_index_path(descriptor_path, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    values = [chunk.to_dict() if hasattr(chunk, "to_dict") else dict(chunk) for chunk in chunks]
    write_json_atomic(path, values)
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
