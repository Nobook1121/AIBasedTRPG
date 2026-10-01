import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from trpg_server.agents.profiles import AgentProfile
from trpg_server.agents.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


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
    knowledge_usage: dict[str, Any] | None = None
    # 非致命异常（请求失败/超时、达到工具轮数上限）时，附带一段要展示给玩家的说明。
    notice: str | None = None
    # 是否因为达到 max_tool_rounds 而被迫收尾。
    rounds_exhausted: bool = False


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


def _truncate_tool_result(result: dict[str, Any], max_chars: int | None) -> tuple[str, str]:
    """Serialize a tool result for re-sending to the model, truncating when it
    exceeds ``max_chars``. Returns ``(payload, display_text)`` where payload is
    what is sent back to the model and display_text is a human-friendly marker.
    The original result is not truncated for UI/tool_messages purposes.
    """
    payload = json.dumps(result, ensure_ascii=False)
    if not max_chars or len(payload) <= max_chars:
        return payload, payload
    truncated = payload[:max_chars]
    marker = "\n…[工具结果已截断：完整结果共 %d 字符，仅保留前 %d 字符]" % (
        len(payload),
        max_chars,
    )
    return truncated + marker, truncated + marker


def _fallback_tool_summary(
    tool_messages: list[dict[str, Any]], direct_messages: list[dict[str, Any]]
) -> str:
    """当模型最终没有返回可显示内容时，用已有工具结果兜底一句话回复。

    保证玩家始终能收到消息，而不是空响应或 500 错误。
    """
    if direct_messages:
        return "已完成场景处理，详情见上方记录。"
    if tool_messages:
        return "已完成检定/场景处理，详情见上方记录。"
    return "本次工具调用较多，但没有生成可显示的回复，请补充你的行动后重试。"


def run_agent_completion(
    requester: Callable[[dict[str, Any]], dict[str, Any]],
    base_payload: dict[str, Any],
    profile: AgentProfile,
    registry: ToolRegistry,
    context: Any,
    max_tool_rounds: int = 8,
    max_tool_result_chars: int | None = None,
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
    knowledge_usage: dict[str, Any] = {
        "ruleset_chunks": 0,
        "ruleset_sources": 0,
        "ruleset_ids": [],
        "knowledge_versions": [],
        "topics": [],
        "citations": [],
        "tool_calls": 0,
    }
    tool_state = getattr(context, "tool_state", None)
    stage_callback = tool_state.get("thinking_stage_callback") if isinstance(tool_state, dict) else None

    def _record_usage(response_data: dict[str, Any] | None) -> None:
        """累计单次请求的 token 用量（含最终的无工具收尾请求）。"""
        nonlocal total_token_count, has_token_count
        nonlocal prompt_token_count, has_prompt_count
        nonlocal completion_token_count, has_completion_count
        nonlocal cached_token_count, has_cached_count
        if not isinstance(response_data, dict):
            return
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

    for _round in range(max_tool_rounds + 1):
        if isinstance(tool_state, dict):
            tool_state["agent_request_rounds"] = _round + 1
        if callable(stage_callback):
            stage_callback("ai_request", "正在请求 AI")
        try:
            response_data = requester(payload)
        except Exception as exc:
            # 请求失败或超时时，不要静默丢弃已经拿到的工具结果；
            # 有可展示内容就带提示返回，否则才作为错误上报。
            logger.warning("Agent request failed on round %s: %s", _round + 1, exc)
            if tool_messages or direct_messages:
                return AgentCompletionResult(
                    content=_fallback_tool_summary(tool_messages, direct_messages),
                    token_count=total_token_count if has_token_count else None,
                    tool_messages=tool_messages,
                    direct_messages=direct_messages,
                    prompt_token_count=prompt_token_count if has_prompt_count else None,
                    completion_token_count=completion_token_count if has_completion_count else None,
                    cached_token_count=cached_token_count if has_cached_count else None,
                    knowledge_usage=knowledge_usage if knowledge_usage["tool_calls"] else None,
                    notice=f"（AI 请求中断：{exc}）",
                )
            return AgentCompletionResult(error=str(exc))
        last_response = response_data
        _record_usage(response_data)
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
            # 重试用尽仍为空：用工具结果兜底，避免返回空内容导致前端报错。
            if not content:
                content = _fallback_tool_summary(tool_messages, direct_messages)
            return AgentCompletionResult(
                content=content,
                token_count=total_token_count if has_token_count else None,
                response_data=response_data,
                tool_messages=tool_messages,
                direct_messages=direct_messages,
                prompt_token_count=prompt_token_count if has_prompt_count else None,
                completion_token_count=completion_token_count if has_completion_count else None,
                cached_token_count=cached_token_count if has_cached_count else None,
                knowledge_usage=knowledge_usage if knowledge_usage["tool_calls"] else None,
            )

        messages.append(_assistant_tool_call_message(message))
        for call in calls:
            function = call.get("function") or {}
            tool_name = str(function.get("name") or "")
            resolved_name, tool = _resolve_tool(tool_name, enabled_by_name)
            if not tool:
                return AgentCompletionResult(error=f"Tool {tool_name} is not enabled for agent {profile.id}")
            if callable(stage_callback):
                stage_callback("tool_call", f"正在执行工具：{resolved_name}")
            if isinstance(tool_state, dict):
                trace = tool_state.setdefault("tool_call_trace", [])
                if isinstance(trace, list):
                    trace.append(resolved_name)
            try:
                arguments = _parse_arguments(function.get("arguments"))
                result = tool.handler(arguments, context)
            except Exception as exc:
                result = {"error": str(exc)}
            if isinstance(result, dict) and result.get("error"):
                import logging
                logging.getLogger(__name__).warning("Agent tool %s failed: %s", resolved_name, result.get("error"))

            reported_usage = result.get("knowledge_usage") if isinstance(result, dict) else None
            if isinstance(reported_usage, dict):
                knowledge_usage["ruleset_chunks"] += int(reported_usage.get("ruleset_chunks") or 0)
                knowledge_usage["ruleset_sources"] += int(reported_usage.get("ruleset_sources") or 0)
                knowledge_usage["tool_calls"] += 1
                for key in ("ruleset_ids", "knowledge_versions", "topics", "citations"):
                    values = reported_usage.get(key)
                    if isinstance(values, list):
                        knowledge_usage[key] = list(dict.fromkeys([*knowledge_usage[key], *[str(value) for value in values if value]]))

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

            result_payload, _ = _truncate_tool_result(result, max_tool_result_chars)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or tool_name,
                    "name": resolved_name,
                    "content": result_payload,
                }
            )

    # 工具轮次用尽：先移除工具、强制模型给出最终叙事；若仍无内容，则用工具结果兜底，
    # 保证玩家一定能收到一条回复，而不是空响应或 500 错误。
    final_payload = {**payload}
    final_payload.pop("tools", None)
    final_payload.pop("tool_choice", None)
    final_payload["messages"] = [
        *messages,
        {
            "role": "system",
            "content": (
                "已达到工具调用上限。请不要再调用任何工具，直接根据以上工具结果生成简洁、"
                "连贯的 KP 叙事回复；若确实没有可叙述的内容，就用一句话说明当前状态。"
            ),
        },
    ]
    if callable(stage_callback):
        stage_callback("ai_request", "正在请求 AI")
    try:
        final_response = requester(final_payload)
    except Exception as exc:
        logger.warning("Agent wrap-up request failed: %s", exc)
        final_response = None
    _record_usage(final_response)
    final_content = str(_extract_message(final_response).get("content") or "").strip()
    if not final_content:
        final_content = _fallback_tool_summary(tool_messages, direct_messages)
    return AgentCompletionResult(
        content=final_content,
        token_count=total_token_count if has_token_count else None,
        response_data=final_response if isinstance(final_response, dict) else last_response,
        tool_messages=tool_messages,
        direct_messages=direct_messages,
        prompt_token_count=prompt_token_count if has_prompt_count else None,
        completion_token_count=completion_token_count if has_completion_count else None,
        cached_token_count=cached_token_count if has_cached_count else None,
        knowledge_usage=knowledge_usage if knowledge_usage["tool_calls"] else None,
        rounds_exhausted=True,
        notice=(
            f"（本次回复已达到最大工具调用轮数 {max_tool_rounds}，KP 已停止继续调用工具并收尾。"
            "如需继续，请再发送一条消息。）"
        ),
    )
