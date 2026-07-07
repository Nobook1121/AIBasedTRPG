import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from trpg_server.agents.profiles import AgentProfile
from trpg_server.agents.tools.base import ToolRegistry
from trpg_server.json_store import read_json, write_json_atomic


DICE_MESSAGE_TOOL_NAMES = {"check.roll_room_check", "dice.roll_coc_check"}


@dataclass(frozen=True)
class AgentCompletionResult:
    content: str = ""
    token_count: int | None = None
    error: str | None = None
    response_data: dict[str, Any] | None = None
    tool_messages: list[dict[str, Any]] | None = None


def _extract_message(response_data: dict[str, Any]) -> dict[str, Any]:
    choices = response_data.get("choices", [])
    if not choices:
        return {}
    return choices[0].get("message") or choices[0].get("delta") or {}


def _extract_token_count(response_data: dict[str, Any]) -> int | None:
    usage = response_data.get("usage") or {}
    if "total_tokens" in usage:
        return usage["total_tokens"]
    if "completion_tokens" in usage and "prompt_tokens" in usage:
        return usage["completion_tokens"] + usage["prompt_tokens"]
    return None


def _parse_arguments(raw_arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not raw_arguments:
        return {}
    return json.loads(raw_arguments)


def _tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(message.get("tool_calls"), list):
        return message["tool_calls"]
    function_call = message.get("function_call")
    if isinstance(function_call, dict):
        return [{"id": "function-call", "type": "function", "function": function_call}]
    return []


def _timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _room_message_time() -> str:
    return time.strftime("%H:%M")


def _append_dice_message(tool_name: str, result: dict[str, Any], context: Any) -> dict[str, Any] | None:
    if tool_name not in DICE_MESSAGE_TOOL_NAMES:
        return None
    if result.get("error"):
        return None
    summary = str(result.get("summary") or "").strip()
    room_dir = getattr(context, "room_dir", None)
    if not summary or not room_dir:
        return None

    message = {
        "id": uuid4().hex,
        "type": "dice",
        "sender_id": None,
        "sender_name": "骰娘",
        "avatar": "/assets/avatars/default_dice.jpg",
        "content": summary,
        "time": _room_message_time(),
        "created_at": _timestamp(),
        "metadata": {
            "tool_name": tool_name,
            "tool_result": result,
        },
    }
    messages_file = room_dir / "messages.json"
    messages = read_json(messages_file, default=[])
    messages.append(message)
    write_json_atomic(messages_file, messages)
    return message


def run_agent_completion(
    requester: Callable[[dict[str, Any]], dict[str, Any]],
    base_payload: dict[str, Any],
    profile: AgentProfile,
    registry: ToolRegistry,
    context: Any,
    max_tool_rounds: int = 4,
) -> AgentCompletionResult:
    payload = {**base_payload}
    messages = list(payload.get("messages", []))
    payload["messages"] = messages
    enabled_tools = registry.select(profile.tool_names)
    if enabled_tools:
        payload["tools"] = [tool.schema() for tool in enabled_tools]
        payload["tool_choice"] = "auto"

    enabled_by_name = {tool.name: tool for tool in enabled_tools}
    last_response = None
    tool_messages = []

    for _round in range(max_tool_rounds + 1):
        response_data = requester(payload)
        last_response = response_data
        message = _extract_message(response_data)
        calls = _tool_calls(message)
        if not calls:
            return AgentCompletionResult(
                content=str(message.get("content") or ""),
                token_count=_extract_token_count(response_data),
                response_data=response_data,
                tool_messages=tool_messages,
            )

        messages.append(message)
        for call in calls:
            function = call.get("function") or {}
            tool_name = str(function.get("name") or "")
            tool = enabled_by_name.get(tool_name)
            if not tool:
                return AgentCompletionResult(error=f"Tool {tool_name} is not enabled for agent {profile.id}")
            try:
                arguments = _parse_arguments(function.get("arguments"))
                result = tool.handler(arguments, context)
            except Exception as exc:
                result = {"error": str(exc)}
            dice_message = _append_dice_message(tool_name, result, context)
            if dice_message:
                tool_messages.append(dice_message)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or tool_name,
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return AgentCompletionResult(error="Agent tool loop limit exceeded", response_data=last_response)
