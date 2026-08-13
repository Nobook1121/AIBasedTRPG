from flask import Blueprint, abort, send_from_directory

from trpg_server.settings import BASE_DIR, FRONTEND_DIST_DIR

bp = Blueprint("pages", __name__)


@bp.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIST_DIR, "index.html")


@bp.route("/<path:path>")
def serve_static(path):
    if path == "data" or path.startswith("data/"):
        abort(404)
    if (FRONTEND_DIST_DIR / path).is_file():
        return send_from_directory(FRONTEND_DIST_DIR, path)
    return send_from_directory(BASE_DIR, path)
