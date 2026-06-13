import json
import logging
import time

import requests
from flask import Blueprint, current_app, request

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.responses import error_response, success_response
from trpg_server.role_config import load_roles, select_role_for_content
from trpg_server.settings import CONFIG_DIR, HISTORY_DIR

bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)


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


def _load_history(user_id):
    history_file = _get_history_dir() / f"{user_id}.json"
    return history_file, read_json(history_file, default=[])


def _select_model(platform_config):
    models = platform_config.get("models", [])
    if not models:
        return "local-model"

    model = next((item for item in models if item.get("enabled", True)), models[0])
    return model.get("id", "local-model")


def _build_messages(system_prompt, history, content):
    messages = [{"role": "system", "content": system_prompt}]
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
        selected_platform, platform_config = _load_enabled_platform(role_config.get("provider"))
        if not platform_config:
            return error_response(
                "No enabled AI platform",
                400,
                "No enabled platform",
            )

        api_key = platform_config.get("config", {}).get("api_key")
        base_url = platform_config.get("config", {}).get("base_url")
        if not base_url:
            return error_response(
                "AI platform config is incomplete",
                400,
                "Incomplete platform config",
            )

        if not api_key and selected_platform == "lmstudio":
            api_key = "lm-studio"
        elif not api_key:
            return error_response(
                "AI platform config is incomplete",
                400,
                "Incomplete platform config",
            )

        history_file, history = _load_history(user_id)
        request_data = {
            "messages": _build_messages(role_config.get("prompt") or _load_kp_prompt(), history, content),
            "model": _select_model(platform_config),
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        logger.info(
            "Sending chat request role=%s platform=%s base_url=%s model=%s user_id=%s request_content=%s",
            role_config.get("id"),
            selected_platform,
            base_url,
            request_data["model"],
            user_id,
            content,
        )
        response = requests.post(base_url, headers=headers, json=request_data, timeout=300)
        if not response.ok:
            return error_response(
                "AI platform request failed",
                response.status_code,
                f"API request failed: {response.status_code}",
            )

        response_data = response.json()
        ai_response, token_count = _extract_ai_response(response_data)
        if not ai_response:
            return error_response(
                "AI platform did not return a response",
                400,
                "No response",
            )
        logger.info(
            "AI response received platform=%s model=%s user_id=%s ai_response=%s",
            selected_platform,
            request_data["model"],
            user_id,
            ai_response,
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

        logger.info("Home message user_id=%s", user_id)
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

        logger.info("Scenario message script_id=%s user_id=%s", script_id, user_id)
        return _message_response(
            user_id,
            message_content,
            "Scenario message sent successfully",
            script_id=script_id,
        )
    except Exception as exc:
        logger.exception("Failed to send scenario message: %s", script_id)
        return error_response("Failed to send scenario message", 500, str(exc))
