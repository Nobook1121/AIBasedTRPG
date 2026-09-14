"""Extensible adapters for external tabletop ruleset knowledge."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from trpg_server.scenario_importer import extract_script_text


@dataclass(frozen=True)
class RulesetChunk:
    ruleset_id: str
    source_id: str
    knowledge_version: str
    chunk_id: str
    topic: str
    rule_scope: str
    locale: str
    title: str
    visibility: str
    priority: int
    text: str
    citation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RulesetAdapter(Protocol):
    ruleset_id: str
    display_name: str
    supported_locales: tuple[str, ...]

    def extract(self, raw: bytes, filename: str) -> str: ...
    def chunk(self, text: str, source: dict[str, Any]) -> list[RulesetChunk]: ...
    def classify_query(self, query: str) -> str | None: ...


class COC7Adapter:
    ruleset_id = "coc7"
    display_name = "Call of Cthulhu 7th Edition"
    supported_locales = ("zh-CN", "en-US")
    _topics = {
        "skill": ("skill", "技能", "专长"), "check": ("check", "检定", "成功", "困难"),
        "opposed_check": ("opposed", "对抗"), "combat": ("combat", "战斗"),
        "damage": ("damage", "伤害"), "weapon": ("weapon", "武器"),
        "sanity": ("sanity", "理智", "san"), "madness": ("madness", "疯狂"),
        "chase": ("chase", "追逐"), "investigation": ("investigation", "调查"),
        "character": ("character", "角色", "属性"), "example": ("example", "示例", "例"),
        "faq": ("faq", "常见问题"),
    }

    def extract(self, raw: bytes, filename: str) -> str:
        return extract_script_text(raw, filename)

    def classify_query(self, query: str) -> str | None:
        value = str(query or "").casefold()
        for topic, words in self._topics.items():
            if any(word.casefold() in value for word in words):
                return topic
        return None

    def chunk(self, text: str, source: dict[str, Any]) -> list[RulesetChunk]:
        source_id = str(source.get("source_id") or "source")
        version = str(source.get("knowledge_version") or "1")
        locale = str(source.get("locale") or "zh-CN")
        sections: list[tuple[str, list[str]]] = []
        title, body = "Core rules", []
        for line in str(text or "").replace("\r", "").split("\n"):
            match = re.match(r"^\s{0,3}(?:#{1,6}|(?:Chapter|第)\s*[0-9一二三四五六七八九十]+)\s*(.*)$", line, re.I)
            if match and match.group(1).strip():
                if body:
                    sections.append((title, body))
                title, body = match.group(1).strip(), []
            else:
                body.append(line)
        if body:
            sections.append((title, body))
        chunks: list[RulesetChunk] = []
        for index, (heading, lines) in enumerate(sections, 1):
            meaningful = [line.rstrip() for line in lines if line.strip()]
            if not meaningful:
                continue
            # Keep formulas, table rows, exceptions, and examples in one semantic block.
            block = "\n".join(meaningful).strip()
            topic = self.classify_query(heading) or "core_rules"
            if re.search(r"例|example", block, re.I):
                topic = "example" if topic == "core_rules" else topic
            chunks.append(RulesetChunk(
                ruleset_id=self.ruleset_id, source_id=source_id, knowledge_version=version,
                chunk_id=f"{source_id}-{index:04d}", topic=topic, rule_scope="coc7-7e",
                locale=locale, title=heading, visibility="global", priority=10,
                text=block, citation=f"{source_id} / {heading}",
            ))
        return chunks


class RulesetRegistry:
    def __init__(self, adapters: list[RulesetAdapter] | None = None):
        self._adapters = {adapter.ruleset_id: adapter for adapter in (adapters or [COC7Adapter()])}

    def get(self, ruleset_id: str) -> RulesetAdapter:
        try:
            return self._adapters[str(ruleset_id)]
        except KeyError as exc:
            raise ValueError(f"Unknown ruleset: {ruleset_id}") from exc

    def list(self) -> list[dict[str, Any]]:
        return [{"ruleset_id": a.ruleset_id, "display_name": a.display_name, "supported_locales": list(a.supported_locales)} for a in self._adapters.values()]
