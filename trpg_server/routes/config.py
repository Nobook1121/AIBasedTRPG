import json
import logging
import re

import requests
from flask import Blueprint, current_app, jsonify, request

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.security import safe_join
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
            return jsonify({"success": False, "message": "Invalid config data"}), 400

        config_path = safe_join(_get_config_dir(), f"{config_name}.toml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(convert_to_toml(config_data), encoding="utf-8")

        logger.info("Config saved file=%s", config_path.name)
        return jsonify({"success": True, "message": "Config saved successfully"})
    except Exception as exc:
        logger.exception("Failed to save config: %s", config_name)
        return jsonify({"success": False, "message": f"Save failed: {exc}"}), 500


@bp.route("/api/config/aiplatform/<platform>", methods=["POST"])
def save_ai_platform_config(platform):
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return jsonify({"success": False, "message": "Invalid config data"}), 400

        config_path = safe_join(_get_ai_platform_dir(), f"{platform}.json")
        write_json_atomic(config_path, config_data)

        logger.info("AI platform config saved platform=%s", platform)
        return jsonify({"success": True, "message": "Config saved successfully"})
    except Exception as exc:
        logger.exception("Failed to save AI platform config: %s", platform)
        return jsonify({"success": False, "message": f"Save failed: {exc}"}), 500


@bp.route("/api/config/aiplatform/<platform>/test", methods=["POST"])
def test_ai_platform_api(platform):
    try:
        test_data = request.get_json(silent=True)
        if not test_data:
            return jsonify({"success": False, "message": "Invalid test data"}), 400

        config_path = safe_join(_get_ai_platform_dir(), f"{platform}.json")
        if not config_path.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Platform config file does not exist",
                    }
                ),
                404,
            )

        config = read_json(config_path, default={})
        api_key = config.get("config", {}).get("api_key")
        base_url = config.get("config", {}).get("base_url")
        if not base_url:
            return jsonify({"success": False, "message": "Base URL is not set"}), 400
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

        logger.info("Testing AI platform API platform=%s base_url=%s", platform, base_url)
        response = requests.post(base_url, headers=headers, json=test_payload, timeout=30)
        response_data = response.json()
        if response.status_code != 200:
            error_message = response_data.get("error", {}).get(
                "message",
                f"API request failed: {response.status_code}",
            )
            return jsonify({"success": False, "error": error_message}), response.status_code

        return jsonify({"success": True, "response": response_data})
    except Exception as exc:
        logger.exception("Failed to test AI platform API: %s", platform)
        return jsonify({"success": False, "error": str(exc)}), 500


@bp.route("/api/config/aimodel/save", methods=["POST"])
def save_model_js_config():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return jsonify({"success": False, "message": "Invalid config data"}), 400

        platform = config_data.get("platform")
        model_id = config_data.get("modelId")
        content = config_data.get("content")
        if not platform or not model_id or not content:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Platform, model ID, and config content are required",
                    }
                ),
                400,
            )

        config_path = safe_join(_get_ai_model_dir(), platform, f"{model_id}.js")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(content, encoding="utf-8")

        logger.info("AI model config saved platform=%s model_id=%s", platform, model_id)
        return jsonify({"success": True, "message": "Config saved successfully"})
    except Exception as exc:
        logger.exception("Failed to save model JS config")
        return jsonify({"success": False, "message": f"Save failed: {exc}"}), 500


@bp.route("/api/config/aimodel/delete", methods=["POST"])
def delete_model_js_config():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return jsonify({"success": False, "message": "Invalid config data"}), 400

        platform = config_data.get("platform")
        model_id = config_data.get("modelId")
        if not platform or not model_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Platform and model ID are required",
                    }
                ),
                400,
            )

        config_path = safe_join(_get_ai_model_dir(), platform, f"{model_id}.js")
        if config_path.exists():
            config_path.unlink()
            logger.info("AI model config deleted platform=%s model_id=%s", platform, model_id)
        else:
            logger.info(
                "AI model config already absent platform=%s model_id=%s",
                platform,
                model_id,
            )

        return jsonify({"success": True, "message": "Config deleted successfully"})
    except Exception as exc:
        logger.exception("Failed to delete model JS config")
        return jsonify({"success": False, "message": f"Delete failed: {exc}"}), 500
