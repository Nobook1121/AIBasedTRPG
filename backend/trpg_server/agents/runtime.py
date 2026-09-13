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
    direct_messages: list[dict[str, Any]] | None = None
    prompt_token_count: int | None = None
    completion_token_count: int | None = None
    cached_token_count: int | None = None


def _extract_message(response_data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(response_data, dict):
        return {}
    choices = response_data.get("choices", [])
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return {}
    return choices[0].get("message") or choices[0].get("delta") or {}


def _extract_token_count(response_data: dict[str, Any]) -> int | None:
    usage = response_data.get("usage") or {}
    if "total_tokens" in usage:
        return usage["total_tokens"]
    if "completion_tokens" in usage and "prompt_tokens" in usage:
        return usage["completion_tokens"] + usage["prompt_tokens"]
    return None


def _extract_usage_counts(response_data: dict[str, Any] | None) -> tuple[int | None, int | None, int | None]:
    usage = (response_data or {}).get("usage") or {}
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    cached = usage.get("cached_tokens") or details.get("cached_tokens") or details.get("cache_read_input_tokens")
    return (
        int(prompt) if prompt is not None else None,
        int(completion) if completion is not None else None,
        int(cached) if cached is not None else None,
    )


def _parse_arguments(raw_arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not raw_arguments:
        return {}
    parsed = json.loads(raw_arguments)
    return parsed if isinstance(parsed, dict) else {}


def _tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(message.get("tool_calls"), list):
        return message["tool_calls"]
    function_call = message.get("function_call")
    if isinstance(function_call, dict):
        return [{"id": "function-call", "type": "function", "function": function_call}]
    return []


def _resolve_tool(tool_name: str, enabled_by_name: dict[str, Any]) -> tuple[str, Any] | tuple[None, None]:
    tool = enabled_by_name.get(tool_name)
    if tool:
        return tool_name, tool
    if "_" in tool_name:
        alias_name = tool_name.replace("_", ".", 1)
        tool = enabled_by_name.get(alias_name)
        if tool:
            return alias_name, tool
    return None, None


def _assistant_tool_call_message(message: dict[str, Any]) -> dict[str, Any]:
    clean_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": message.get("tool_calls", []),
    }
    if "function_call" in message:
        clean_message["function_call"] = message["function_call"]
    return clean_message


def run_agent_completion(
    requester: Callable[[dict[str, Any]], dict[str, Any]],
    base_payload: dict[str, Any],
    profile: AgentProfile,
    registry: ToolRegistry,
    context: Any,
    max_tool_rounds: int = 8,
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
    tool_messages: list[dict[str, Any]] = []
    direct_messages: list[dict[str, Any]] = []
    empty_completion_retries = 0
    total_token_count = 0
    has_token_count = False
    prompt_token_count = 0
    completion_token_count = 0
    cached_token_count = 0
    has_prompt_count = False
    has_completion_count = False
    has_cached_count = False

    for _round in range(max_tool_rounds + 1):
        response_data = requester(payload)
        last_response = response_data
        round_token_count = _extract_token_count(response_data)
        round_prompt, round_completion, round_cached = _extract_usage_counts(response_data)
        if round_prompt is not None:
            prompt_token_count += round_prompt
            has_prompt_count = True
        if round_completion is not None:
            completion_token_count += round_completion
            has_completion_count = True
        if round_cached is not None:
            cached_token_count += round_cached
            has_cached_count = True
        if round_token_count is not None:
            total_token_count += round_token_count
            has_token_count = True
        message = _extract_message(response_data)
        calls = _tool_calls(message)
        if not calls:
            content = str(message.get("content") or "")
            # Some providers occasionally return an empty assistant message
            # after a tool call (or transiently on a normal completion). Give
            # the model one chance to continue before reporting no response.
            if not content and empty_completion_retries < 2:
                empty_completion_retries += 1
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "上一轮生成没有返回可显示内容。请继续生成简洁的KP回复；"
                            "如果刚才使用了工具，请根据工具结果作出叙事判断，除非条件确实满足，否则不要再次调用触发器工具。"
                        ),
                    }
                )
                continue
            return AgentCompletionResult(
                content=content,
                token_count=total_token_count if has_token_count else None,
                response_data=response_data,
                tool_messages=tool_messages,
                direct_messages=direct_messages,
                prompt_token_count=prompt_token_count if has_prompt_count else None,
                completion_token_count=completion_token_count if has_completion_count else None,
                cached_token_count=cached_token_count if has_cached_count else None,
            )

        messages.append(_assistant_tool_call_message(message))
        for call in calls:
            function = call.get("function") or {}
            tool_name = str(function.get("name") or "")
            resolved_name, tool = _resolve_tool(tool_name, enabled_by_name)
            if not tool:
                return AgentCompletionResult(error=f"Tool {tool_name} is not enabled for agent {profile.id}")
            try:
                arguments = _parse_arguments(function.get("arguments"))
                result = tool.handler(arguments, context)
            except Exception as exc:
                result = {"error": str(exc)}
            if isinstance(result, dict) and result.get("error"):
                import logging
                logging.getLogger(__name__).warning("Agent tool %s failed: %s", resolved_name, result.get("error"))

            tool_state = getattr(context, "tool_state", None)
            if isinstance(tool_state, dict) and isinstance(result, dict):
                tool_state["last_tool"] = resolved_name
                if resolved_name in {"check.roll_room_check", "dice.roll_coc_check"}:
                    tool_state["last_check"] = result

            if isinstance(result, dict) and result.get("direct_message"):
                direct_message = result["direct_message"]
                if isinstance(direct_message, dict):
                    direct_messages.append(direct_message)

            if isinstance(result, dict) and isinstance(result.get("visible_message"), dict):
                tool_messages.append(result["visible_message"])

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or tool_name,
                    "name": resolved_name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return AgentCompletionResult(
        error="Agent tool loop limit exceeded",
        token_count=total_token_count if has_token_count else None,
        response_data=last_response,
        tool_messages=tool_messages,
        direct_messages=direct_messages,
        prompt_token_count=prompt_token_count if has_prompt_count else None,
        completion_token_count=completion_token_count if has_completion_count else None,
        cached_token_count=cached_token_count if has_cached_count else None,
    )
