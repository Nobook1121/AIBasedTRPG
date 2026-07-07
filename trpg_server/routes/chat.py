import json
import logging
import re
import time
from copy import deepcopy
from urllib.parse import quote

import requests
from flask import Blueprint, current_app, request, session

from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.agents.context import build_agent_context
from trpg_server.agents.profiles import resolve_agent_profile
from trpg_server.agents.runtime import run_agent_completion
from trpg_server.agents.tools import default_tool_registry
from trpg_server.agents.tools.room import get_room_snapshot
from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.logging_config import log_user_action, user_action_text
from trpg_server.responses import error_response, success_response
from trpg_server.role_config import load_roles, select_role_for_content
from trpg_server.settings import CONFIG_DIR, HISTORY_DIR, ROOMS_DIR, SCENARIOS_DIR

bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)
_HISTORY_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _message_response(user_id, content, message, script_id=None):
    payload = {
        "user_id": user_id,
        "content": content,
        "timestamp": _timestamp(),
    }
    if script_id is not None:
        payload["script_id"] = script_id

    return success_response(payload, message)


def _get_ai_platform_dir():
    return current_app.config.get("AI_PLATFORM_DIR", CONFIG_DIR / "aiplatform")


def _get_config_dir():
    return current_app.config.get("CONFIG_DIR", CONFIG_DIR)


def _get_history_dir():
    return current_app.config.get("HISTORY_DIR", HISTORY_DIR)


def _get_kp_prompt_file():
    return current_app.config.get("KP_PROMPT_FILE", CONFIG_DIR / "roles" / "kp.md")


def _get_role_config_file():
    return current_app.config.get("ROLE_CONFIG_FILE", CONFIG_DIR / "roles" / "roles.json")


def _load_enabled_platform(provider_id=None):
    platform_dir = _get_ai_platform_dir()
    if not platform_dir.exists():
        logger.warning("AI platform config directory does not exist: %s", platform_dir)
        return None, None

    for path in platform_dir.glob("*.json"):
        if provider_id and path.stem != provider_id:
            continue
        try:
            config = read_json(path, default={})
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to read AI platform config: %s", path.name)
            continue

        if config.get("enabled", False):
            return path.stem, config

    return None, None


def _load_role_for_content(content):
    roles = load_roles(_get_role_config_file(), _get_kp_prompt_file(), _get_ai_platform_dir())
    return select_role_for_content(roles, content)


def _json_for_log(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _provider_api_format(platform_config):
    return str(platform_config.get("api_format") or platform_config.get("interface") or "openai").lower()


def _provider_runtime_config(platform_config):
    config = platform_config.get("config") or {}
    return config if isinstance(config, dict) else {}


def _resolve_provider_endpoint(platform_config, payload=None):
    config = _provider_runtime_config(platform_config)
    endpoint_url = str(config.get("endpoint_url") or "").strip()
    if endpoint_url:
        return endpoint_url.rstrip("/")

    base_url = str(config.get("base_url") or "").strip().rstrip("/")
    api_format = _provider_api_format(platform_config)
    if not base_url:
        return ""

    if api_format == "anthropic":
        if base_url.endswith("/v1/messages"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/messages"
        return f"{base_url}/v1/messages"

    if api_format == "custom":
        return base_url

    if api_format == "anythingllm":
        if base_url.endswith("/chat"):
            return base_url
        workspace_slug = str(config.get("workspace_slug") or "").strip()
        if isinstance(payload, dict):
            workspace_slug = workspace_slug or str(payload.get("model") or "").strip()
        if not workspace_slug:
            return base_url
        if base_url.endswith("/api"):
            base_url = f"{base_url}/v1"
        return f"{base_url}/workspace/{quote(workspace_slug, safe='')}/chat"

    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def _provider_headers(platform_config):
    config = _provider_runtime_config(platform_config)
    api_format = _provider_api_format(platform_config)
    headers = {"Content-Type": "application/json"}

    configured_headers = config.get("headers")
    if isinstance(configured_headers, dict):
        headers.update({str(key): str(value) for key, value in configured_headers.items()})

    api_key = str(config.get("api_key") or "").strip()
    if api_format == "anthropic":
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = str(config.get("anthropic_version") or "2023-06-01")
        headers.pop("Authorization", None)
        return headers

    if api_key and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _last_user_message(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


def _replace_template_values(value, payload):
    if isinstance(value, dict):
        return {key: _replace_template_values(item, payload) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_template_values(item, payload) for item in value]
    if not isinstance(value, str):
        return value

    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    replacements = {
        "{{model}}": payload.get("model"),
        "{{messages}}": messages,
        "{{last_user_message}}": _last_user_message(messages),
    }
    if value in replacements:
        return replacements[value]

    result = value
    for placeholder, replacement in replacements.items():
        if placeholder in result:
            result = result.replace(placeholder, json.dumps(replacement, ensure_ascii=False) if isinstance(replacement, (dict, list)) else str(replacement or ""))
    return result


def _build_anthropic_request(payload):
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    system_messages = [str(item.get("content") or "") for item in messages if item.get("role") == "system"]
    anthropic_messages = []
    for item in messages:
        role = item.get("role")
        if role == "system":
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        anthropic_messages.append({"role": role, "content": item.get("content") or ""})

    request_data = {
        "model": payload.get("model"),
        "messages": anthropic_messages,
        "max_tokens": payload.get("max_tokens", 4096),
    }
    if system_messages:
        request_data["system"] = "\n\n".join(system_messages)
    for key in ("temperature", "top_p", "stream"):
        if key in payload:
            request_data[key] = payload[key]
    return request_data


def _build_anythingllm_request(platform_config, payload):
    config = _provider_runtime_config(platform_config)
    request_data = {
        "message": _last_user_message(payload.get("messages") if isinstance(payload.get("messages"), list) else []),
        "mode": str(config.get("anythingllm_mode") or "chat"),
        "attachments": [],
        "reset": False,
    }
    session_id = str(config.get("session_id") or "").strip()
    if session_id:
        request_data["sessionId"] = session_id
    return request_data


def _build_provider_request(platform_config, payload):
    api_format = _provider_api_format(platform_config)
    if api_format == "anthropic":
        return _build_anthropic_request(payload)
    if api_format == "anythingllm":
        return _build_anythingllm_request(platform_config, payload)
    if api_format == "custom":
        custom = platform_config.get("custom") if isinstance(platform_config.get("custom"), dict) else {}
        template = custom.get("request_template")
        if isinstance(template, dict):
            return _replace_template_values(deepcopy(template), payload)
    request_data = payload.copy()
    extra_body = request_data.pop("extra_body", None)
    if isinstance(extra_body, dict):
        request_data.update(extra_body)
    return request_data


def _value_at_path(value, path):
    current = value
    for part in str(path or "").split("."):
        if not part:
            continue
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _extract_openai_response(response_data):
    ai_response = ""
    choices = response_data.get("choices", [])
    if choices:
        choice = choices[0]
        if "message" in choice and "content" in choice["message"]:
            ai_response = choice["message"]["content"]
        elif "delta" in choice and "content" in choice["delta"]:
            ai_response = choice["delta"]["content"]

    token_count = None
    usage = response_data.get("usage")
    if usage:
        if "total_tokens" in usage:
            token_count = usage["total_tokens"]
        elif "completion_tokens" in usage and "prompt_tokens" in usage:
            token_count = usage["completion_tokens"] + usage["prompt_tokens"]

    return ai_response, token_count


def _extract_anthropic_response(response_data):
    content = response_data.get("content") if isinstance(response_data, dict) else []
    text = ""
    if isinstance(content, list):
        text = "".join(str(item.get("text") or "") for item in content if isinstance(item, dict) and item.get("type") == "text")
    usage = response_data.get("usage") if isinstance(response_data, dict) else {}
    token_count = None
    if isinstance(usage, dict):
        output_tokens = usage.get("output_tokens")
        input_tokens = usage.get("input_tokens")
        if isinstance(output_tokens, int) and isinstance(input_tokens, int):
            token_count = output_tokens + input_tokens
        elif isinstance(output_tokens, int):
            token_count = output_tokens
    return text, token_count


def _extract_anythingllm_response(response_data):
    if isinstance(response_data, dict):
        value = response_data.get("textResponse")
        if value is not None:
            return str(value), None
        value = response_data.get("error")
        if value is not None:
            return str(value), None
    return "", None


def _extract_provider_response(platform_config, response_data):
    api_format = _provider_api_format(platform_config)
    if api_format == "anthropic":
        return _extract_anthropic_response(response_data)
    if api_format == "anythingllm":
        return _extract_anythingllm_response(response_data)
    if api_format == "custom":
        custom = platform_config.get("custom") if isinstance(platform_config.get("custom"), dict) else {}
        value = _value_at_path(response_data, custom.get("response_path"))
        return (str(value), None) if value is not None else ("", None)
    return _extract_openai_response(response_data)


def _normalize_provider_response(platform_config, response_data):
    if _provider_api_format(platform_config) == "openai":
        return response_data

    content, token_count = _extract_provider_response(platform_config, response_data)
    normalized = {"choices": [{"message": {"role": "assistant", "content": content}}]}
    if token_count is not None:
        normalized["usage"] = {"total_tokens": token_count}
    return normalized


def _post_ai_request(base_url, headers):
    def requester(payload):
        logger.info("AI API request payload: %s", _json_for_log(payload))
        response = requests.post(base_url, headers=headers, json=payload, timeout=300)
        if not response.ok:
            raise RuntimeError(f"API request failed: {response.status_code}")
        response_data = response.json()
        logger.info("AI API response payload: %s", _json_for_log(response_data))
        return response_data

    return requester


def _post_provider_request(platform_config):
    headers = _provider_headers(platform_config)

    def requester(payload):
        endpoint = _resolve_provider_endpoint(platform_config, payload)
        request_payload = _build_provider_request(platform_config, payload)
        logger.info("AI API request payload: %s", _json_for_log(request_payload))
        response = requests.post(endpoint, headers=headers, json=request_payload, timeout=300)
        if not response.ok:
            raise RuntimeError(f"API request failed: {response.status_code}")
        response_data = response.json()
        logger.info("AI API response payload: %s", _json_for_log(response_data))
        return _normalize_provider_response(platform_config, response_data)

    return requester



def _load_kp_prompt():
    prompt_path = _get_kp_prompt_file()
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to load KP prompt file: {prompt_path}") from exc

    content_lines = [
        line for line in content.splitlines() if not line.startswith("#") and line.strip()
    ]
    if content_lines:
        return "\n".join(content_lines)

    return "你是KP（守密人），负责主持TRPG游戏，引导玩家进行游戏。"


def _safe_history_part(value):
    text = str(value or "unknown").strip() or "unknown"
    return _HISTORY_SAFE_RE.sub("_", text)[:120]


def _history_filename(user_id, room_id=None, agent_id="kp"):
    safe_agent = _safe_history_part(agent_id)
    if room_id:
        return f"room-{_safe_history_part(room_id)}-{safe_agent}.json"
    return f"user-{_safe_history_part(user_id)}-{safe_agent}.json"


def _load_history(user_id, room_id=None, agent_id="kp"):
    history_file = _get_history_dir() / _history_filename(user_id, room_id, agent_id)
    return history_file, read_json(history_file, default=[])


def _select_model(platform_config):
    models = platform_config.get("models", [])
    if not models:
        return "local-model"

    model = next((item for item in models if item.get("enabled", True)), models[0])
    return model.get("id", "local-model")


def _room_snapshot_system_message(snapshot):
    room = snapshot.get("room") or {}
    scenario = snapshot.get("scenario") or {}
    members = snapshot.get("members") or []
    memory = (snapshot.get("memory") or {}).get("items") or []

    lines = [
        "当前房间资料由 function `room.get_room_snapshot` 读取。",
        "这是本次回复必须优先采用的当前房间、绑定剧本和调查员摘要上下文；不得沿用其他房间的剧本、角色或记忆。",
        f"房间：{room.get('name') or '未命名房间'}（ID：{room.get('id') or 'unknown'}）。",
    ]
    if scenario:
        lines.append(f"绑定剧本：{scenario.get('title') or room.get('scenario_title') or '未命名剧本'}。")
        summary = scenario.get("summary")
        if summary:
            lines.append(str(summary))
    else:
        lines.append("绑定剧本：未读取到。")

    if members:
        lines.append("当前玩家与调查员摘要：")
        for member in members:
            character = member.get("character") or {}
            character_name = character.get("name") or "未绑定调查员"
            character_summary = character.get("summary") or "暂无叙事背景摘要。"
            lines.append(f"- {member.get('username') or 'unknown'}：{character_name}。{character_summary}")
    else:
        lines.append("当前玩家与调查员摘要：暂无活跃玩家。")

    if memory:
        lines.append("房间记忆摘要：")
        for item in memory[:10]:
            content = str(item.get("content") or "").strip()
            if content:
                lines.append(f"- {content}")

    return "\n".join(lines)


def _build_messages(system_prompt, history, content, room_snapshot_message=None):
    messages = [{"role": "system", "content": system_prompt}]
    if room_snapshot_message:
        messages.append({"role": "system", "content": room_snapshot_message})
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": content})
    return messages


def _extract_ai_response(response_data):
    ai_response = ""
    choices = response_data.get("choices", [])
    if choices:
        choice = choices[0]
        if "message" in choice and "content" in choice["message"]:
            ai_response = choice["message"]["content"]
        elif "delta" in choice and "content" in choice["delta"]:
            ai_response = choice["delta"]["content"]

    token_count = None
    usage = response_data.get("usage")
    if usage:
        if "total_tokens" in usage:
            token_count = usage["total_tokens"]
        elif "completion_tokens" in usage and "prompt_tokens" in usage:
            token_count = usage["completion_tokens"] + usage["prompt_tokens"]

    return ai_response, token_count


@bp.route("/api/chat", methods=["POST"])
def chat():
    try:
        message_data = request.get_json(silent=True)
        if not message_data:
            return error_response("Please provide message data", 400, "No data")

        user_id = message_data.get("user_id", "unknown")
        content = message_data.get("content", "")
        role_config = _load_role_for_content(content)
        agent_profile = resolve_agent_profile(role_config, _get_kp_prompt_file())
        selected_platform, platform_config = _load_enabled_platform(agent_profile.provider)
        if not platform_config:
            return error_response(
                "No enabled AI platform",
                400,
                "No enabled platform",
            )

        runtime_config = platform_config.get("config", {})
        if not isinstance(runtime_config, dict):
            runtime_config = {}
        api_key = runtime_config.get("api_key")
        base_url = _resolve_provider_endpoint(platform_config)
        if not base_url:
            return error_response(
                "AI platform config is incomplete",
                400,
                "Incomplete platform config",
            )

        if not api_key and selected_platform == "lmstudio":
            runtime_config["api_key"] = "lm-studio"
        elif not api_key and _provider_api_format(platform_config) in {"openai", "anthropic"}:
            return error_response(
                "AI platform config is incomplete",
                400,
                "Incomplete platform config",
            )

        room_id = message_data.get("room_id")
        agent_context = build_agent_context(
            room_id=room_id,
            rooms_dir=current_app.config.get("ROOMS_DIR", ROOMS_DIR),
            scenarios_dir=current_app.config.get("SCENARIOS_DIR", SCENARIOS_DIR),
            user_id=user_id,
            agent_id=agent_profile.id,
        )
        room_snapshot_message = None
        if room_id:
            room_snapshot_message = _room_snapshot_system_message(get_room_snapshot({}, agent_context))

        history_file, history = _load_history(user_id, room_id=room_id, agent_id=agent_profile.id)
        runtime_config = load_ai_runtime_config(_get_config_dir())
        request_data = {
            "messages": _build_messages(
                agent_profile.prompt or _load_kp_prompt(),
                history,
                content,
                room_snapshot_message=room_snapshot_message,
            ),
            "model": _select_model(platform_config),
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        if runtime_config.stream_output:
            request_data["stream"] = False

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "发起了 AI 对话"),
            用户ID=session.get("user_id") or user_id,
            角色=role_config.get("id"),
            平台=selected_platform,
            模型=request_data["model"],
            内容长度=len(content),
        )
        result = run_agent_completion(
            requester=_post_provider_request(platform_config),
            base_payload=request_data,
            profile=agent_profile,
            registry=default_tool_registry(),
            context=agent_context,
        )
        if result.error:
            return error_response("AI agent request failed", 500, result.error)

        ai_response = result.content
        token_count = result.token_count
        if not ai_response:
            return error_response(
                "AI platform did not return a response",
                400,
                "No response",
            )
        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "收到了 AI 对话回复"),
            用户ID=session.get("user_id") or user_id,
            平台=selected_platform,
            模型=request_data["model"],
            回复长度=len(ai_response),
            Token数=token_count,
        )

        history.extend(
            [
                {"role": "user", "content": content},
                {"role": "assistant", "content": ai_response},
            ]
        )
        write_json_atomic(history_file, history[-20:])

        return success_response(
            message=None,
            content=ai_response,
            token_count=token_count,
            tool_messages=result.tool_messages or [],
        )
    except requests.exceptions.Timeout:
        return error_response("AI platform request timeout", 504, "Request timeout")
    except requests.exceptions.ConnectionError:
        return error_response("Cannot connect to AI platform", 503, "Connection error")
    except json.JSONDecodeError as exc:
        logger.exception("Failed to parse AI platform response")
        return error_response("Failed to parse AI platform response", 500, str(exc))
    except Exception as exc:
        logger.exception("Chat request failed")
        return error_response("Chat request failed", 500, str(exc))


@bp.route("/api/messages", methods=["POST"])
def send_home_message():
    try:
        message_data = request.get_json(silent=True)
        if not message_data:
            return error_response("Please provide message data", 400, "No data")

        user_id = message_data.get("user_id", "unknown")
        message_content = message_data.get("content", "")
        if not message_content:
            return error_response(
                "Please provide message content",
                400,
                "No message content",
            )

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "发送了主页对话"),
            用户ID=session.get("user_id") or user_id,
            内容长度=len(message_content),
        )
        return _message_response(user_id, message_content, "Message sent successfully")
    except Exception as exc:
        logger.exception("Failed to send home message")
        return error_response("Failed to send message", 500, str(exc))


@bp.route("/api/scenarios/<int:script_id>/messages", methods=["POST"])
def send_message(script_id):
    try:
        message_data = request.get_json(silent=True)
        if not message_data:
            return error_response("Please provide message data", 400, "No data")

        user_id = message_data.get("user_id", "unknown")
        message_content = message_data.get("content", "")
        if not message_content:
            return error_response(
                "Please provide message content",
                400,
                "No message content",
            )

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "发送了剧本对话"),
            用户ID=session.get("user_id") or user_id,
            剧本ID=script_id,
            内容长度=len(message_content),
        )
        return _message_response(
            user_id,
            message_content,
            "Scenario message sent successfully",
            script_id=script_id,
        )
    except Exception as exc:
        logger.exception("Failed to send scenario message: %s", script_id)
        return error_response("Failed to send scenario message", 500, str(exc))
