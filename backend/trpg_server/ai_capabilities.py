"""AI 平台能力探测：判断配置的 OpenAI 兼容端点是否支持 Responses API。

只有 Responses API（``/responses``）支持 ``previous_response_id`` 这种有状态续答：
多轮工具调用之间新增的上下文交给服务端保存，客户端只发增量，能显著降低重复计费。
多数兼容端点并不具备该能力，所以这里做一次轻量、真实的探测（两次请求确认），
把结论交给用户决定是否启用，而不是默认打开。
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

CHAT_COMPLETIONS_SUFFIX = "/chat/completions"
RESPONSES_SUFFIX = "/responses"
_VERSION_SUFFIX_RE = re.compile(r"/v\d+$", re.IGNORECASE)


def chat_completions_endpoint(base_url: str) -> str:
    """把用户填写的 Base URL 规范成完整的 chat/completions 端点。

    用户在设置页填写的可能只是主机名（``https://api.deepseek.com``）、带版本号的
    前缀（``https://api.deepseek.com/v1``）或完整端点。这里只在「发请求」这一步做
    补齐，不再回写用户的输入——即使用户只填主机名也能正常调用。
    """
    text = str(base_url or "").strip().rstrip("/")
    if not text:
        return ""
    if text.endswith(CHAT_COMPLETIONS_SUFFIX):
        return text
    if _VERSION_SUFFIX_RE.search(text):
        return text + CHAT_COMPLETIONS_SUFFIX
    return f"{text}/v1{CHAT_COMPLETIONS_SUFFIX}"


def responses_endpoint(base_url: str) -> str:
    """从 chat/completions 地址推导 Responses API 地址。

    兼容平台通常把两个端点放在同一前缀下：``.../v1/chat/completions`` → ``.../v1/responses``。
    """
    text = chat_completions_endpoint(base_url)
    if not text:
        return ""
    return text[: -len(CHAT_COMPLETIONS_SUFFIX)] + RESPONSES_SUFFIX


def _error_detail(data: Any, status: Any) -> str:
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(error, str):
            return error
    return f"HTTP {status}" if status else "no response"


def probe_responses_api(
    base_url: str,
    api_key: str | None,
    model: str,
    timeout: int = 15,
    post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """探测平台是否真正支持 ``previous_response_id``。

    分两步，只有两步都成功才算支持——第一步确认 ``/responses`` 可用并拿到 ``id``，
    第二步用该 ``id`` 作为 ``previous_response_id`` 续答。任一环节失败都返回不支持，
    并把状态码与错误摘要一起返回，方便前端展示原因。
    """
    endpoint = responses_endpoint(base_url)
    if not endpoint:
        return {"supported": False, "status": None, "detail": "base_url is not set", "endpoint": ""}
    if not model:
        return {"supported": False, "status": None, "detail": "an enabled model is required", "endpoint": endpoint}

    sender = post or requests.post
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key or ''}"}

    first = _post_json(sender, endpoint, headers, {"model": model, "input": "ping", "store": True}, timeout)
    status, data = first
    response_id = data.get("id") if isinstance(data, dict) else None
    if status != 200 or not response_id or not isinstance(data.get("output"), list):
        return {"supported": False, "status": status, "detail": _error_detail(data, status), "endpoint": endpoint}

    second = _post_json(
        sender,
        endpoint,
        headers,
        {"model": model, "input": "ping", "store": True, "previous_response_id": response_id},
        timeout,
    )
    status, data = second
    if status != 200:
        return {
            "supported": False,
            "status": status,
            "detail": f"previous_response_id is not accepted: {_error_detail(data, status)}",
            "endpoint": endpoint,
        }
    return {"supported": True, "status": status, "detail": "", "endpoint": endpoint}


def _post_json(sender: Callable[..., Any], endpoint: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> tuple[int | None, Any]:
    try:
        response = sender(endpoint, headers=headers, json=payload, timeout=timeout)
    except Exception as exc:  # 网络异常视为不支持，不阻塞用户在设置页的操作
        logger.info("Responses API probe request failed for %s: %s", endpoint, exc)
        return None, {"error": {"message": str(exc)}}
    try:
        return response.status_code, response.json()
    except Exception:
        return getattr(response, "status_code", None), None