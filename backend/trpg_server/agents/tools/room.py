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
                "character_card": member.get("character_card"),
                "character_state": member.get("character_state"),
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

    available_sections = {}
    for key in ("scenes", "locations", "npcs", "clues", "endings"):
        values = scenario.get(key)
        if isinstance(values, list) and values:
            available_sections[key] = len(values)
    summary = {
        "id": scenario.get("id"),
        "title": scenario.get("title"),
        "description": scenario.get("description"),
        "found": True,
        "available_sections": available_sections,
    }
    return summary


def _summarize_character_card(character_card: Any) -> dict[str, Any] | None:
    if not isinstance(character_card, dict):
        return None

    summary = {}
    for key in ("id", "name", "occupation", "age", "gender", "sex"):
        value = character_card.get(key)
        if value not in (None, ""):
            summary[key] = value
    return summary or None


def _summarize_character_state(character_state: Any) -> dict[str, Any] | None:
    if not isinstance(character_state, dict):
        return None

    summary = {}
    for key in ("max_hp", "current_hp", "max_san", "current_san"):
        value = character_state.get(key)
        if value is not None:
            summary[key] = value
    return summary or None


def _summarize_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summarized = []
    for member in members:
        summary = {
            "user_id": member.get("user_id"),
            "username": member.get("username"),
            "active": member.get("active"),
        }
        character = _summarize_character_card(member.get("character_card"))
        if character:
            summary["character"] = character
        character_state = _summarize_character_state(member.get("character_state"))
        if character_state:
            summary["character_state"] = character_state
        summarized.append(summary)
    return summarized


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
        "members": _summarize_members(characters["members"]),
        "memory": read_room_memory({"limit": int(arguments.get("memory_limit") or 20)}, context),
    }


GET_ROOM_SNAPSHOT_TOOL = AgentTool(
    name="room.get_room_snapshot",
    description=(
        "Load a compact current-room snapshot with bound scenario identity, member names, "
        "character identities, HP/SAN state, and memory. Use room.get_character_cards for full stats."
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
    description="Load character cards and HP/SAN state for current room members.",
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
