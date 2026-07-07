import json
from typing import Any

from trpg_server.agents.memory import read_room_memory, remember_room_fact
from trpg_server.agents.tools.base import AgentTool
from trpg_server.json_store import read_json


def _find_scenario(scenarios_dir, scenario_id):
    if not scenarios_dir or scenario_id is None or not scenarios_dir.exists():
        return None
    for path in scenarios_dir.glob("*.json"):
        scenario = read_json(path, default={})
        if str(scenario.get("id")) == str(scenario_id):
            return scenario
    return None


def _matches_query(value: Any, query: str) -> bool:
    if not query:
        return True
    return query.casefold() in json.dumps(value, ensure_ascii=False).casefold()


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _first_text(mapping: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _as_text(mapping.get(key))
        if text:
            return text
    return ""


def _compact(value: str, limit: int = 160) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _summarize_list_items(label: str, values: Any, max_items: int = 5) -> list[str]:
    if not isinstance(values, list):
        return []
    lines = []
    for index, item in enumerate(values[:max_items], start=1):
        if not isinstance(item, dict):
            text = _as_text(item)
            if text:
                lines.append(f"{label}{index}：{_compact(text)}")
            continue
        title = _first_text(item, ("title", "name", "id")) or f"{label}{index}"
        detail = _first_text(item, ("summary", "description", "content", "background", "text"))
        lines.append(f"{label}{index}：{_compact(title + ('，' + detail if detail else ''))}")
    return lines


def _summarize_scenario_text(scenario: dict[str, Any] | None, room_info: dict[str, Any]) -> str:
    if not scenario:
        title = _as_text(room_info.get("scenario_title")) or "未找到剧本"
        return f"当前房间绑定剧本：{title}。剧本文件未找到，若需要细节应再次确认房间绑定。"

    parts = [f"剧本《{_as_text(scenario.get('title')) or '未命名剧本'}》。"]
    for key in ("description", "background", "preparation"):
        text = _as_text(scenario.get(key))
        if text:
            parts.append(_compact(text, 220))
    for label, key in (("场景", "scenes"), ("地点", "locations"), ("NPC", "npcs"), ("线索", "clues"), ("结局", "endings")):
        parts.extend(_summarize_list_items(label, scenario.get(key)))
    return "\n".join(parts)


def _summarize_background(background: Any) -> str:
    if isinstance(background, str):
        return _compact(background)
    if not isinstance(background, dict):
        return ""
    values = []
    for key in ("story", "personalDescription", "ideology", "significantPeople", "meaningfulLocations", "treasuredPossessions", "traits", "injuries", "phobias", "tomes"):
        text = _as_text(background.get(key))
        if text:
            values.append(text)
    return _compact("；".join(values), 220)


def _summarize_character(card: Any) -> dict[str, Any] | None:
    if not isinstance(card, dict):
        return None
    summary_parts = []
    occupation = _as_text(card.get("occupation"))
    era = _as_text(card.get("era"))
    age = _as_text(card.get("age"))
    residence = _as_text(card.get("residence"))
    birthplace = _as_text(card.get("birthplace"))
    background = _summarize_background(card.get("background"))
    for label, text in (("职业", occupation), ("时代", era), ("年龄", age), ("现居地", residence), ("出生地", birthplace), ("背景", background)):
        if text:
            summary_parts.append(f"{label}：{text}")
    return {
        "id": card.get("id"),
        "name": _as_text(card.get("name")) or "未命名调查员",
        "summary": "；".join(summary_parts) if summary_parts else "暂无叙事背景摘要。",
    }


def get_room_scenario_context(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    info = context.room_info()
    scenario = _find_scenario(context.scenarios_dir, info.get("scenario_id"))
    if not scenario:
        return {"scenario": None, "matches": [], "message": "current room scenario was not found"}

    query = str(arguments.get("query") or "").strip()
    scene_id = str(arguments.get("scene_id") or "").strip()
    max_items = max(1, min(20, int(arguments.get("max_items") or 5)))
    candidates = []
    for key in ("scenes", "locations", "npcs", "clues"):
        values = scenario.get(key)
        if isinstance(values, list):
            for item in values:
                if scene_id and str(item.get("id", "")) != scene_id:
                    continue
                if _matches_query(item, query):
                    candidates.append({"section": key, **item})
    return {
        "scenario": {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
            "description": scenario.get("description"),
        },
        "matches": candidates[:max_items],
    }


def get_room_character_cards(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    include_inactive = bool(arguments.get("include_inactive", False))
    members = []
    for member in context.room_info().get("members", []):
        active = member.get("is_active", True) is not False and member.get("status", "active") != "removed"
        if not include_inactive and not active:
            continue
        members.append(
            {
                "user_id": member.get("user_id"),
                "username": member.get("username"),
                "active": active,
                "character": _summarize_character(member.get("character_card")),
            }
        )
    return {"members": members}


def _summarize_scenario(scenario: dict[str, Any] | None, room_info: dict[str, Any]) -> dict[str, Any] | None:
    if not scenario:
        scenario_id = room_info.get("scenario_id")
        if scenario_id is None:
            return None
        return {
            "id": scenario_id,
            "title": room_info.get("scenario_title"),
            "found": False,
            "scenes": [],
        }

    summary = {
        "id": scenario.get("id"),
        "title": scenario.get("title"),
        "found": True,
        "summary": _summarize_scenario_text(scenario, room_info),
    }
    return summary


def get_room_snapshot(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    info = context.room_info()
    scenario = _find_scenario(context.scenarios_dir, info.get("scenario_id"))
    characters = get_room_character_cards(
        {"include_inactive": bool(arguments.get("include_inactive", False))},
        context,
    )
    return {
        "room": {
            "id": info.get("id") or context.room_id,
            "name": info.get("name"),
            "scenario_id": info.get("scenario_id"),
            "scenario_title": info.get("scenario_title"),
        },
        "scenario": _summarize_scenario(scenario, info),
        "members": characters["members"],
        "memory": read_room_memory({"limit": int(arguments.get("memory_limit") or 20)}, context),
    }


GET_ROOM_SNAPSHOT_TOOL = AgentTool(
    name="room.get_room_snapshot",
    description=(
        "Load the current room, bound scenario summary, and active investigators' narrative summaries. "
        "Does not expose numeric character values; use check.roll_room_check for checks."
    ),
    parameters={
        "type": "object",
        "properties": {
            "include_inactive": {"type": "boolean"},
            "memory_limit": {"type": "integer", "minimum": 1, "maximum": 50},
        },
    },
    handler=get_room_snapshot,
)


GET_SCENARIO_CONTEXT_TOOL = AgentTool(
    name="room.get_scenario_context",
    description="Load scenario scenes, NPCs, clues, and locations for the current room.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "scene_id": {"type": "string"},
            "max_items": {"type": "integer", "minimum": 1, "maximum": 20},
        },
    },
    handler=get_room_scenario_context,
)

GET_CHARACTER_CARDS_TOOL = AgentTool(
    name="room.get_character_cards",
    description=(
        "Load current room members' investigator narrative summary only. Does not expose numeric character "
        "values; use check.roll_room_check for checks."
    ),
    parameters={"type": "object", "properties": {"include_inactive": {"type": "boolean"}}},
    handler=get_room_character_cards,
)

GET_MEMORY_TOOL = AgentTool(
    name="room.get_memory",
    description="Read remembered facts for the current room.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
    },
    handler=read_room_memory,
)

REMEMBER_FACT_TOOL = AgentTool(
    name="room.remember_fact",
    description="Persist an important room fact for future KP continuity.",
    parameters={
        "type": "object",
        "properties": {
            "kind": {"type": "string"},
            "content": {"type": "string"},
            "importance": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["content"],
    },
    handler=remember_room_fact,
)
