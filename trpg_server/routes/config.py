import json
import logging
import re

import requests
from flask import Blueprint, current_app, request

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.responses import error_response, success_response
from trpg_server.role_config import enabled_provider_options, load_roles, save_role
from trpg_server.security import require_permission, safe_join
from trpg_server.settings import CONFIG_DIR

bp = Blueprint("config", __name__)
logger = logging.getLogger(__name__)
_BARE_TOML_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _get_config_dir():
    return current_app.config.get("CONFIG_DIR", CONFIG_DIR)


def _get_ai_platform_dir():
    return current_app.config.get("AI_PLATFORM_DIR", _get_config_dir() / "aiplatform")


def _get_ai_model_dir():
    return current_app.config.get("AI_MODEL_DIR", _get_config_dir() / "aimodel")


def _get_kp_prompt_file():
    return current_app.config.get("KP_PROMPT_FILE", _get_config_dir() / "roles" / "kp.md")


def _get_role_config_file():
    return current_app.config.get("ROLE_CONFIG_FILE", _get_config_dir() / "roles" / "roles.json")


def _format_toml_value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _format_toml_key(key):
    key_text = str(key)
    if _BARE_TOML_KEY_RE.fullmatch(key_text):
        return key_text
    return json.dumps(key_text, ensure_ascii=False)


def convert_to_toml(config_data):
    lines = []
    for section, values in config_data.items():
        if not isinstance(values, dict):
            continue

        lines.append(f"[{_format_toml_key(section)}]")
        for key, value in values.items():
            lines.append(f"{_format_toml_key(key)} = {_format_toml_value(value)}")
        lines.append("")

    return "\n".join(lines)


@bp.route("/api/config/<config_name>", methods=["POST"])
def save_config(config_name):
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return error_response("Invalid config data", 400)

        config_path = safe_join(_get_config_dir(), f"{config_name}.toml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(convert_to_toml(config_data), encoding="utf-8")

        logger.debug("Config saved file=%s", config_path.name)
        return success_response(message="Config saved successfully")
    except Exception as exc:
        logger.exception("Failed to save config: %s", config_name)
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/config/aiplatform/<platform>", methods=["POST"])
def save_ai_platform_config(platform):
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return error_response("Invalid config data", 400)

        config_path = safe_join(_get_ai_platform_dir(), f"{platform}.json")
        write_json_atomic(config_path, config_data)

        logger.debug("AI platform config saved platform=%s", platform)
        return success_response(message="Config saved successfully")
    except Exception as exc:
        logger.exception("Failed to save AI platform config: %s", platform)
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/config/aiplatform/<platform>/test", methods=["POST"])
def test_ai_platform_api(platform):
    try:
        test_data = request.get_json(silent=True)
        if not test_data:
            return error_response("Invalid test data", 400)

        config_path = safe_join(_get_ai_platform_dir(), f"{platform}.json")
        if not config_path.exists():
            return error_response("Platform config file does not exist", 404)

        config = read_json(config_path, default={})
        api_key = config.get("config", {}).get("api_key")
        base_url = config.get("config", {}).get("base_url")
        if not base_url:
            return error_response("Base URL is not set", 400)
        if not api_key and platform == "lmstudio":
            api_key = "lm-studio"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        test_payload = test_data.copy()
        if "extra_body" in test_payload:
            extra_body = test_payload.pop("extra_body")
            test_payload.update(extra_body)

        logger.debug("Testing AI platform API platform=%s base_url=%s", platform, base_url)
        response = requests.post(base_url, headers=headers, json=test_payload, timeout=30)
        response_data = response.json()
        if response.status_code != 200:
            error_message = response_data.get("error", {}).get(
                "message",
                f"API request failed: {response.status_code}",
            )
            return error_response(None, response.status_code, error_message)

        return success_response(message=None, response=response_data)
    except Exception as exc:
        logger.exception("Failed to test AI platform API: %s", platform)
        return error_response(None, 500, str(exc))


@bp.route("/api/config/aimodel/save", methods=["POST"])
def save_model_request_config():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return error_response("Invalid config data", 400)

        platform = config_data.get("platform")
        model_id = config_data.get("modelId")
        content = config_data.get("content")
        if not platform or not model_id or not content:
            return error_response("Platform, model ID, and config content are required", 400)

        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                return error_response("Model config content must be valid JSON", 400)
        if not isinstance(content, dict):
            return error_response("Model config content must be a JSON object", 400)

        config_path = safe_join(_get_ai_model_dir(), platform, f"{model_id}.json")
        write_json_atomic(config_path, content)

        legacy_js_path = safe_join(_get_ai_model_dir(), platform, f"{model_id}.js")
        if legacy_js_path.exists():
            legacy_js_path.unlink()

        logger.debug("AI model request config saved platform=%s model_id=%s", platform, model_id)
        return success_response(message="Config saved successfully")
    except Exception as exc:
        logger.exception("Failed to save model request config")
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/config/system-prompt", methods=["GET"])
@require_permission("ADMIN")
def get_system_prompt():
    prompt_path = _get_kp_prompt_file()
    try:
        if not prompt_path.exists():
            return success_response(data={"content": ""})
        return success_response(data={"content": prompt_path.read_text(encoding="utf-8")})
    except OSError as exc:
        logger.exception("Failed to load system prompt")
        return error_response(f"Load failed: {exc}", 500)


@bp.route("/api/config/system-prompt", methods=["POST"])
@require_permission("ADMIN")
def save_system_prompt():
    try:
        prompt_data = request.get_json(silent=True)
        if not isinstance(prompt_data, dict):
            return error_response("Invalid prompt data", 400)

        content = prompt_data.get("content")
        if not isinstance(content, str):
            return error_response("Prompt content is required", 400)

        prompt_path = _get_kp_prompt_file()
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(content, encoding="utf-8")

        logger.info("System prompt saved file=%s", prompt_path.name)
        return success_response(message="System prompt saved successfully")
    except Exception as exc:
        logger.exception("Failed to save system prompt")
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/config/roles", methods=["GET"])
@require_permission("ADMIN")
def get_role_configs():
    try:
        roles = load_roles(_get_role_config_file(), _get_kp_prompt_file(), _get_ai_platform_dir())
        providers = enabled_provider_options(_get_ai_platform_dir())
        return success_response(data={"roles": roles, "enabled_providers": providers})
    except Exception as exc:
        logger.exception("Failed to load role configs")
        return error_response(f"Load failed: {exc}", 500)


@bp.route("/api/config/roles/<role_id>", methods=["POST"])
@require_permission("ADMIN")
def save_role_config(role_id):
    try:
        role_data = request.get_json(silent=True)
        if not isinstance(role_data, dict):
            return error_response("Invalid role config data", 400)

        roles = save_role(
            _get_role_config_file(),
            _get_kp_prompt_file(),
            _get_ai_platform_dir(),
            role_id,
            role_data,
        )
        logger.info("Role config saved role_id=%s provider=%s", role_id, role_data.get("provider"))
        return success_response(message="Role config saved successfully", data={"roles": roles})
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception as exc:
        logger.exception("Failed to save role config: %s", role_id)
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/config/aimodel/delete", methods=["POST"])
def delete_model_request_config():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return error_response("Invalid config data", 400)

        platform = config_data.get("platform")
        model_id = config_data.get("modelId")
        if not platform or not model_id:
            return error_response("Platform and model ID are required", 400)

        removed = False
        for suffix in (".json", ".js"):
            config_path = safe_join(_get_ai_model_dir(), platform, f"{model_id}{suffix}")
            if config_path.exists():
                config_path.unlink()
                removed = True

        if removed:
            logger.debug("AI model request config deleted platform=%s model_id=%s", platform, model_id)
        else:
            logger.debug("AI model request config already absent platform=%s model_id=%s", platform, model_id)

        return success_response(message="Config deleted successfully")
    except Exception as exc:
        logger.exception("Failed to delete model request config")
        return error_response(f"Delete failed: {exc}", 500)
