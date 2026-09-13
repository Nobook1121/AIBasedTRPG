import json

from flask import Blueprint, Response, current_app, send_from_directory

from trpg_server.ai_platform_config import load_public_platform_config
from trpg_server.security import safe_join

from trpg_server.settings import (
    AI_PLATFORM_ASSETS_DIR,
    AI_PLATFORM_SECRET_DIR,
    AVATARS_DIR,
    CHARACTERS_DIR,
    CONFIG_DIR,
    SCENARIO_COVERS_DIR,
    SCENARIOS_DIR,
    TOOLS_DIR,
    VENDOR_ASSETS_DIR,
)

bp = Blueprint("assets", __name__)


def _get_config_dir():
    return current_app.config.get("CONFIG_DIR", CONFIG_DIR)


def _get_ai_platform_secret_dir():
    return current_app.config.get("AI_PLATFORM_SECRET_DIR", AI_PLATFORM_SECRET_DIR)


def _with_no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@bp.route("/assets/avatars/<path:filename>")
def serve_avatar(filename):
    return _with_no_cache(send_from_directory(AVATARS_DIR, filename))


@bp.route("/assets/scenario_covers/<path:filename>")
def serve_scenario_cover(filename):
    return _with_no_cache(send_from_directory(SCENARIO_COVERS_DIR, filename))


@bp.route("/assets/scenarios/<path:filename>")
def serve_scenario_asset(filename):
    return _with_no_cache(send_from_directory(SCENARIOS_DIR, filename))


@bp.route("/assets/aiplatform/<path:filename>")
def serve_aiplatform_icon(filename):
    return _with_no_cache(send_from_directory(AI_PLATFORM_ASSETS_DIR, filename))


@bp.route("/assets/vendor/<path:filename>")
def serve_vendor_asset(filename):
    return send_from_directory(VENDOR_ASSETS_DIR, filename)


@bp.route("/config/<path:filename>")
def serve_config(filename):
    if filename.startswith("aiplatform/") and filename.endswith(".json"):
        config_path = safe_join(_get_config_dir(), filename)
        if config_path.exists():
            secret_path = safe_join(_get_ai_platform_secret_dir(), filename.split("/", 1)[1])
            config = load_public_platform_config(config_path, secret_path)
            response = Response(json.dumps(config, ensure_ascii=False, indent=2) + "\n", mimetype="application/json")
            return _with_no_cache(response)
    return send_from_directory(_get_config_dir(), filename)


@bp.route("/data/characters/<path:filename>")
def serve_character_data(filename):
    return _with_no_cache(send_from_directory(CHARACTERS_DIR, filename))
