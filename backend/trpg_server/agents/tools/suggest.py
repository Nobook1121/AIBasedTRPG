from typing import Any

from trpg_server.agents.tools.base import AgentTool

MAX_SUGGESTED_ACTIONS = 5
MAX_ACTION_CHARS = 80


def _suggestions_enabled(context: Any) -> bool:
    """Resolve whether action suggestions may be produced for this request.

    ``routes/chat.py`` records the authoritative decision (global hint switch
    AND room house rule) in ``tool_state``. Direct tool users that do not pass
    through chat fall back to the room house rule alone.
    """
    state = getattr(context, "tool_state", None)
    if isinstance(state, dict) and "allow_action_suggestions" in state:
        return bool(state.get("allow_action_suggestions"))
    room_info = context.room_info() if hasattr(context, "room_info") else {}
    house_rules = room_info.get("house_rules") if isinstance(room_info, dict) else {}
    return bool((house_rules or {}).get("action_suggestions_enabled"))


def _clean_actions(actions: Any) -> list[str]:
    if not isinstance(actions, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in actions:
        text = str(item or "").strip()[:MAX_ACTION_CHARS]
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
        if len(cleaned) >= MAX_SUGGESTED_ACTIONS:
            break
    return cleaned


def suggest_actions(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    """Stage player-perspective action options for the chat UI.

    The staged list is delivered to the triggering player (and broadcast as
    read-only buttons to the rest of the room) by the chat route; it is never
    written into the model's narration or persisted as a room message.
    """
    if not _suggestions_enabled(context):
        return {"error": "action suggestions are disabled by the room house rules"}

    actions = _clean_actions(arguments.get("actions"))
    if not actions:
        return {"error": "actions must be a non-empty list of short action phrases"}

    state = getattr(context, "tool_state", None)
    if isinstance(state, dict):
        state["suggested_actions"] = actions
        state["suggested_actions_owner"] = getattr(context, "user_id", None)

    return {
        "suggested_actions": actions,
        "status": "displayed_to_players",
        "instruction": "请在叙事中继续描述当前情境，不要把这些选项再次写进正文或 options 字段。",
    }


SUGGEST_ACTIONS_TOOL = AgentTool(
    name="room.suggest_actions",
    description=(
        "由房间房规开启时可用。当你希望向玩家提示可行的下一步行动时调用此工具，"
        "返回玩家视角的 2-5 条简短行为短语（如「四处走动」「看看周围」）。"
        "调用后不要再把可选操作列进叙事正文或 options 字段。"
        "若房规未开启该功能，请不要调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "玩家视角的可选行动短语，2-5 条，每条尽量简短。",
            }
        },
        "required": ["actions"],
    },
    handler=suggest_actions,
)