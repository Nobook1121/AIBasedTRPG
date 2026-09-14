from typing import Any

from trpg_server.agents.tools.base import AgentTool
from trpg_server.scenario_store import build_trigger_message, find_trigger_by_id, load_scenario_by_id


def _condition_requires_check(condition: str) -> bool:
    text = condition.casefold()
    return any(
        marker in text
        for marker in ("检定", "鉴定", "判定", "技能", "属性", "灵感", "check", "roll", "skill", "attribute")
    )


def reveal_scenario_trigger(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    room_info = context.room_info()
    scenario_id = room_info.get("scenario_id")
    if scenario_id in (None, ""):
        return {"error": "current room has no bound scenario"}

    trigger_id = arguments.get("trigger_id") or arguments.get("id")
    if trigger_id in (None, ""):
        return {"error": "trigger_id is required"}

    scenarios_dir = context.scenarios_dir
    if not scenarios_dir:
        return {"error": "scenarios directory is not configured"}

    _, scenario = load_scenario_by_id(scenarios_dir, scenario_id, scenario_version=room_info.get("scenario_version"))
    if not scenario:
        return {"error": f"scenario {scenario_id} was not found"}

    trigger = find_trigger_by_id(scenario, trigger_id)
    if not trigger:
        return {"error": f"trigger {trigger_id} was not found"}

    condition = str(trigger.get("condition") or "").strip()
    condition_met = arguments.get("condition_met")
    tool_state = getattr(context, "tool_state", {}) or {}
    is_explicit_trigger_request = bool(tool_state.get("allow_unconditional_trigger"))
    if not condition and not is_explicit_trigger_request:
        return {
            "error": (
                "trigger has no explicit condition; do not reveal it automatically. "
                "A room manager must use the manual trigger command."
            ),
            "trigger_id": trigger_id,
        }
    if condition:
        if not isinstance(condition_met, bool):
            return {
                "error": "condition_met must be provided for conditional triggers",
                "trigger_id": trigger_id,
                "condition": condition,
            }
        if _condition_requires_check(condition):
            check_result = tool_state.get("last_check")
            if not isinstance(check_result, dict) or "success" not in check_result:
                return {
                    "error": "conditional trigger requires a preceding dice/check tool result",
                    "trigger_id": trigger_id,
                    "condition": condition,
                }
            check_name = str(arguments.get("check_name") or "").strip()
            if check_name and str(check_result.get("name") or check_result.get("skill") or "").casefold() != check_name.casefold():
                return {
                    "error": "the preceding check does not match check_name",
                    "trigger_id": trigger_id,
                    "condition": condition,
                }
            if bool(check_result.get("success")) != condition_met:
                return {
                    "error": "condition_met does not match the preceding check result",
                    "trigger_id": trigger_id,
                    "condition": condition,
                    "check_success": bool(check_result.get("success")),
                }
        if not condition_met:
            return {
                "triggered": False,
                "trigger_id": trigger_id,
                "condition": condition,
                "message": "trigger condition was not met",
            }

    message = build_trigger_message(scenario, trigger_id)
    if not message:
        return {"error": f"trigger {trigger_id} was not found"}

    return {
        "triggered": True,
        "condition": condition,
        "direct_message": message,
        "message": message,
    }


REVEAL_SCENARIO_TRIGGER_TOOL = AgentTool(
    name="trigger.reveal_scenario_trigger",
    description=(
        "Reveal a stored scenario trigger by numeric id after its condition has been evaluated. "
        "For check-based conditions, a preceding check.roll_room_check or dice.roll_coc_check result is required. "
        "Do not invent trigger content."
    ),
    parameters={
        "type": "object",
        "properties": {
            "trigger_id": {"type": "integer", "minimum": 1},
            "condition_met": {
                "type": "boolean",
                "description": "Whether the trigger condition is satisfied after evaluating the current action and any check result.",
            },
            "check_name": {
                "type": "string",
                "description": "The skill or attribute name used by the preceding check, when applicable.",
            },
        },
        "required": ["trigger_id"],
    },
    handler=reveal_scenario_trigger,
)
