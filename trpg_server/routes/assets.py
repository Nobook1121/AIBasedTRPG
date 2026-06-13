from flask import Blueprint, send_from_directory

from trpg_server.settings import (
    AVATARS_DIR,
    CHARACTERS_DIR,
    CONFIG_DIR,
    SCENARIO_COVERS_DIR,
    BASE_DIR,
)

bp = Blueprint("assets", __name__)


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


@bp.route("/assets/aiplatform/<path:filename>")
def serve_aiplatform_icon(filename):
    return _with_no_cache(send_from_directory(BASE_DIR / "assets" / "aiplatform", filename))


@bp.route("/config/<path:filename>")
def serve_config(filename):
    return send_from_directory(CONFIG_DIR, filename)


@bp.route("/data/characters/<path:filename>")
def serve_character_data(filename):
    return _with_no_cache(send_from_directory(CHARACTERS_DIR, filename))
