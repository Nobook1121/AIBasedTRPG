from __future__ import annotations

from flask import Blueprint, current_app, request

from trpg_server.agents.ruleset_knowledge import RulesetKnowledgeStore
from trpg_server.responses import error_response, success_response
from trpg_server.security import is_allowed_upload, require_permission_node
from trpg_server.settings import KNOWLEDGE_BASES_DIR, ROOMS_DIR

bp = Blueprint("knowledge_bases", __name__)
ALLOWED_EXTENSIONS = {"txt", "md", "markdown", "text", "doc", "docx"}


def _store() -> RulesetKnowledgeStore:
    root = current_app.config.get("KNOWLEDGE_BASES_DIR", KNOWLEDGE_BASES_DIR)
    rooms = current_app.config.get("ROOMS_DIR", ROOMS_DIR)
    return RulesetKnowledgeStore(root, rooms_dir=rooms)


@bp.route("/api/knowledge-bases/rulesets", methods=["GET"])
@require_permission_node("settings.knowledge_bases")
def list_rulesets():
    return success_response(data=_store().list_rulesets())


@bp.route("/api/knowledge-bases/<ruleset_id>/sources", methods=["GET"])
@require_permission_node("settings.knowledge_bases")
def list_sources(ruleset_id):
    return success_response(data=_store()._meta(ruleset_id).get("sources", []))


@bp.route("/api/knowledge-bases/<ruleset_id>/sources", methods=["POST"])
@require_permission_node("settings.knowledge_bases")
def upload_source(ruleset_id):
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename or not is_allowed_upload(uploaded.filename, ALLOWED_EXTENSIONS):
        return error_response("Unsupported or missing file", 400)
    raw = uploaded.read()
    max_size = int(current_app.config.get("KNOWLEDGE_BASE_MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    if len(raw) > max_size:
        return error_response("File is too large", 413)
    try:
        source = _store().upload_source(ruleset_id, uploaded.filename, raw, request.form.get("locale", "zh-CN"))
        result = _store().reindex(ruleset_id)
        return success_response(data={"source": source, "version": result}, status=201)
    except (ValueError, OSError) as exc:
        return error_response(str(exc), 400)


@bp.route("/api/knowledge-bases/<ruleset_id>/reindex", methods=["POST"])
@require_permission_node("settings.knowledge_bases")
def reindex(ruleset_id):
    try:
        return success_response(data=_store().reindex(ruleset_id))
    except (ValueError, OSError) as exc:
        return error_response(str(exc), 400)


@bp.route("/api/knowledge-bases/<ruleset_id>/enable", methods=["POST"])
@require_permission_node("settings.knowledge_bases")
def enable(ruleset_id):
    store = _store(); meta = store._meta(ruleset_id); meta["enabled"] = True; data = store._registry(); data[ruleset_id] = meta; store._save_registry(data)
    return success_response(data=meta)


@bp.route("/api/knowledge-bases/<ruleset_id>/archive", methods=["POST"])
@require_permission_node("settings.knowledge_bases")
def archive(ruleset_id):
    return success_response(data=_store().archive(ruleset_id))


@bp.route("/api/rooms/<room_id>/rulesets", methods=["POST"])
@require_permission_node("settings.knowledge_bases")
def bind_room_ruleset(room_id):
    payload = request.get_json(silent=True) or {}
    ruleset_id = payload.get("ruleset_id")
    if not ruleset_id:
        return error_response("ruleset_id is required", 400)
    try:
        return success_response(data=_store().bind_room(room_id, ruleset_id, payload.get("knowledge_version")))
    except (ValueError, OSError) as exc:
        return error_response(str(exc), 400)
