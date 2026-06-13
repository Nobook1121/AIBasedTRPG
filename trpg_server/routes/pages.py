from flask import Blueprint, abort, send_from_directory

from trpg_server.settings import BASE_DIR

bp = Blueprint("pages", __name__)


@bp.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")


@bp.route("/<path:path>")
def serve_static(path):
    if path == "data" or path.startswith("data/"):
        abort(404)
    return send_from_directory(BASE_DIR, path)
