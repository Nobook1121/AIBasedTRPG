import json
from typing import Any

from trpg_server.agents.memory import read_room_memory, remember_room_fact
from trpg_server.agents.tools.base import AgentTool
from trpg_server.scenario_store import build_trigger_message, iter_scenario_trigger_catalog, load_scenario_by_id
from trpg_server.json_store import write_json_atomic


def _find_scenario(scenarios_dir, scenario_id):
    if not scenarios_dir or scenario_id is None or not scenarios_dir.exists():
        return None
    _, scenario = load_scenario_by_id(scenarios_dir, scenario_id)
    return scenario


def _matches_query(value: Any, query: str) -> bool:
    if not query:
        return True
    return query.casefold() in json.dumps(value, ensure_ascii=False).casefold()


def _module_type(module: dict[str, Any]) -> str:
    return str(module.get("module_type") or module.get("type") or "").strip().lower()


def _fallback_modules(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for index, item in enumerate(scenario.get("scenes", []) if isinstance(scenario.get("scenes"), list) else []):
        if isinstance(item, dict):
            modules.append(
                {
                    "id": item.get("module_id") or item.get("id") or f"scene-{index + 1}",
                    "module_type": "scene",
                    "title": item.get("title") or f"场景 {index + 1}",
                    "summary": item.get("marker") or "",
                    "content": item.get("content") or "",
                    "triggers": item.get("triggers", []) if isinstance(item.get("triggers", []), list) else [],
                }
            )
    for index, item in enumerate(scenario.get("endings", []) if isinstance(scenario.get("endings"), list) else []):
        if isinstance(item, dict):
            modules.append(
                {
                    "id": item.get("module_id") or item.get("id") or f"ending-{index + 1}",
                    "module_type": "ending",
                    "title": item.get("title") or f"结局 {index + 1}",
                    "summary": item.get("marker") or "",
                    "content": item.get("content") or "",
                }
            )
    return modules


def _scenario_modules(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    modules = scenario.get("modules")
    if isinstance(modules, list):
        return [module for module in modules if isinstance(module, dict)]
    return []


def _summarize_module(module: dict[str, Any], include_content: bool = False) -> dict[str, Any]:
    summary = {
        "id": module.get("id"),
        "module_type": _module_type(module),
        "title": module.get("title"),
        "summary": module.get("summary") or module.get("marker"),
        "visibility": module.get("visibility"),
        "send_to_ai": module.get("send_to_ai"),
    }
    if module.get("code"):
        summary["code"] = module.get("code")
    if module.get("open_ending") is not None:
        summary["open_ending"] = module.get("open_ending")
    if _module_type(module) == "opening":
        summary["fixed_opening"] = bool(module.get("fixed_opening", False))
    if include_content and module.get("content"):
        summary["content"] = module.get("content")
    if _module_type(module) == "scene" and isinstance(module.get("triggers"), list):
        summary["trigger_count"] = len(module["triggers"])
    if _module_type(module) == "custom" and isinstance(module.get("inputs"), list):
        summary["input_count"] = len(module["inputs"])
    return summary


def _collect_available_sections(scenario: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for module in _scenario_modules(scenario):
        module_type = _module_type(module)
        counts[module_type] = counts.get(module_type, 0) + 1
    if counts:
        if counts.get("scene"):
            counts["scenes"] = counts["scene"]
        if counts.get("ending"):
            counts["endings"] = counts["ending"]
        return counts
    return counts


def _scene_manifest(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a small deterministic index; full text is never included here."""
    manifest = []
    for order, module in enumerate(_scenario_modules(scenario), 1):
        if _module_type(module) not in {"scene", "ending"}:
            continue
        summary = str(module.get("summary") or module.get("marker") or "").strip()
        manifest.append({
            "id": str(module.get("scene_id") or module.get("id")),
            "module_id": str(module.get("id")),
            "type": _module_type(module),
            "title": str(module.get("title") or ""),
            "summary": summary[:120],
            "order": module.get("source_order", order),
        })
    return manifest


def _global_manifest(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Compact immutable facts sent with the room index."""
    result = []
    for module in _scenario_modules(scenario):
        module_type = _module_type(module)
        if module_type not in {"opening", "background", "public_info", "timeline"}:
            continue
        result.append({
            "id": str(module.get("id")),
            "type": module_type,
            "title": str(module.get("title") or ""),
            "summary": str(module.get("summary") or module.get("marker") or "")[:180],
        })
    return result


def _find_module(scenario: dict[str, Any], module_id: str | None = None, module_type: str | None = None, scene_id: str | None = None) -> dict[str, Any] | None:
    for module in _scenario_modules(scenario):
        if module_id and str(module.get("id")) == module_id:
            return module
        if scene_id and str(module.get("scene_id") or module.get("id")) == scene_id:
            return module
        if module_type and _module_type(module) == module_type:
            return module
    return None


def get_room_scenario_context(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    info = context.room_info()
    scenario = _find_scenario(context.scenarios_dir, info.get("scenario_id"))
    if not scenario:
        return {"scenario": None, "matches": [], "message": "current room scenario was not found"}

    query = str(arguments.get("query") or "").strip()
    scene_id = str(arguments.get("scene_id") or "").strip()
    module_type = str(arguments.get("module_type") or "").strip().lower()
    max_items = max(1, min(20, int(arguments.get("max_items") or 5)))

    candidates = []
    for module in _scenario_modules(scenario):
        if scene_id and str(module.get("scene_id") or module.get("id")) != scene_id:
            continue
        if module_type and _module_type(module) != module_type:
            continue
        if _matches_query(
            {
                "title": module.get("title"),
                "summary": module.get("summary") or module.get("marker"),
                "content": module.get("content"),
                "code": module.get("code"),
                "module_type": module.get("module_type"),
            },
            query,
        ):
            candidates.append(_summarize_module(module, include_content=False))

    return {
        "scenario": {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
            "description": scenario.get("description") or scenario.get("notes"),
            "allow_open_ending": scenario.get("allow_open_ending", False),
            "module_count": len(_scenario_modules(scenario)),
            "available_sections": _collect_available_sections(scenario),
            "active_scene_id": info.get("active_scene_id"),
            "scene_manifest": _scene_manifest(scenario),
            "global_manifest": _global_manifest(scenario),
        },
        "matches": candidates[:max_items],
        "triggers": iter_scenario_trigger_catalog(scenario, scene_id=scene_id or None),
    }


def get_room_scenario_module(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    info = context.room_info()
    scenario = _find_scenario(context.scenarios_dir, info.get("scenario_id"))
    if not scenario:
        return {"error": "current room scenario was not found"}

    module_id = str(arguments.get("module_id") or arguments.get("id") or "").strip()
    module_type = str(arguments.get("module_type") or "").strip().lower() or None
    scene_id = str(arguments.get("scene_id") or "").strip() or None
    module = _find_module(scenario, module_id=module_id or None, module_type=module_type, scene_id=scene_id)
    if not module:
        return {"error": "scenario module was not found"}

    return {
        "scenario": {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
        },
        "module": module,
    }


def activate_scenario_scene(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    """Persist the active scene after an explicit player/KP transition.

    The scene must exist in the bound scenario. This gives the model a stable
    pointer between turns and makes it impossible to silently switch to an
    invented location.
    """
    if not context.room_dir:
        return {"error": "room context is required"}
    info = context.room_info()
    scenario = _find_scenario(context.scenarios_dir, info.get("scenario_id"))
    if not scenario:
        return {"error": "current room scenario was not found"}
    scene_id = str(arguments.get("scene_id") or arguments.get("module_id") or "").strip()
    if not scene_id:
        return {"error": "scene_id is required"}
    # Direct tool users (e.g. administrators/tests) may omit request_content;
    # model calls from chat must be backed by an explicit transition request.
    if getattr(context, "request_content", "") and not getattr(context, "tool_state", {}).get("allow_scene_transition"):
        return {"error": "scene transition requires an explicit player transition"}
    if getattr(context, "request_content", "") and getattr(context, "tool_state", {}).get("allow_scene_transition"):
        context.tool_state["scene_transition_verified"] = True
    module = _find_module(scenario, scene_id=scene_id, module_id=scene_id)
    if not module or _module_type(module) not in {"scene", "ending"}:
        return {"error": "scene_id is not present in the bound scenario", "scene_id": scene_id}
    info["active_scene_id"] = str(module.get("scene_id") or module.get("id"))
    info["active_scene_title"] = module.get("title")
    write_json_atomic(context.room_dir / "info.json", info)
    context.tool_state["active_scene_id"] = info["active_scene_id"]
    return {"activated": True, "active_scene_id": info["active_scene_id"],
            "module": _summarize_module(module, include_content=False)}


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
            "available_sections": {},
        }

    return {
        "id": scenario.get("id"),
        "title": scenario.get("title"),
        "description": scenario.get("description") or scenario.get("notes"),
        "found": True,
        "available_sections": _collect_available_sections(scenario),
        "allow_open_ending": scenario.get("allow_open_ending", False),
        "module_count": len(_scenario_modules(scenario)),
        "trigger_count": len(iter_scenario_trigger_catalog(scenario)),
        "active_scene_id": room_info.get("active_scene_id"),
        "scene_manifest": _scene_manifest(scenario),
        "global_manifest": _global_manifest(scenario),
    }


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
            "active_scene_id": info.get("active_scene_id"),
            "active_scene_title": info.get("active_scene_title"),
        },
        "scenario": _summarize_scenario(scenario, info),
        "members": _summarize_members(characters["members"]),
        "memory": read_room_memory({"limit": int(arguments.get("memory_limit") or 20)}, context),
        # Trigger metadata is loaded only when the model asks for scenario context.
        # Keeping it out of every snapshot reduces prompt size and prevents unrelated
        # scene triggers from being treated as current actions.
        "triggers": [],
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
    description="Load scenario module summaries for the current room, including scenes, endings, NPCs, monsters, and custom modules.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "scene_id": {"type": "string"},
            "module_type": {"type": "string"},
            "max_items": {"type": "integer", "minimum": 1, "maximum": 20},
        },
    },
    handler=get_room_scenario_context,
)


GET_SCENARIO_MODULE_TOOL = AgentTool(
    name="room.get_scenario_module",
    description="Load the full content of one scenario module by module id, scene id, or module type.",
    parameters={
        "type": "object",
        "properties": {
            "module_id": {"type": "string"},
            "module_type": {"type": "string"},
            "scene_id": {"type": "string"},
        },
    },
    handler=get_room_scenario_module,
)


ACTIVATE_SCENARIO_SCENE_TOOL = AgentTool(
    name="room.activate_scenario_scene",
    description=(
        "Persist the current scene/ending by an id from scene_manifest. Use only when the player "
        "explicitly enters, leaves, or transitions to that scene; never invent an id."
    ),
    parameters={
        "type": "object",
        "properties": {"scene_id": {"type": "string"}, "module_id": {"type": "string"}},
        "required": ["scene_id"],
    },
    handler=activate_scenario_scene,
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
