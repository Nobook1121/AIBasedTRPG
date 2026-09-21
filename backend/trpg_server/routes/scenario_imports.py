from __future__ import annotations
import json, time
from pathlib import Path
from flask import Blueprint, Response, current_app, request, session
from trpg_server.responses import error_response, success_response
from trpg_server.scenario_import_jobs import public_job_payload, submit_import_job
from trpg_server.scenario_documents import validate_scenario_upload, ScenarioDocumentError
from trpg_server.scenario_store import load_scenario_record, save_scenario_record, scenario_descriptor_paths
from trpg_server.agents.knowledge_base import persist_knowledge_index, KnowledgeBaseService

bp = Blueprint("scenario_imports", __name__)

def _store(): return current_app.extensions["scenario_import_store"]
def _job(job_id):
    job = _store().get(job_id)
    if not job or str(job.get("owner_id")) != str(session.get("user_id")): return None
    return job
def _login():
    if not session.get("user_id"): return error_response("Authentication required", 401, "Authentication required")
    return None

@bp.post("/api/scripts/import")
def create_import():
    if (e := _login()): return e
    uploaded = request.files.get("file")
    if not uploaded: return error_response("Please provide a file", 400, "No file")
    raw = uploaded.read()
    try: validate_scenario_upload(uploaded.filename or "script.txt", len(raw), current_app.config["SCENARIO_IMPORT_MAX_BYTES"])
    except ScenarioDocumentError as exc: return error_response(str(exc), 400, "Invalid script")
    filename = Path(uploaded.filename or "script.txt").name
    job = _store().create(owner_id=str(session["user_id"]), filename=filename, metadata={k: request.form.get(k, "") for k in ("title", "author", "description", "public")})
    source = Path(_store().root) / job["id"] / "source" / filename; source.parent.mkdir(parents=True, exist_ok=True); source.write_bytes(raw)
    submit_import_job(current_app._get_current_object(), job["id"])
    return success_response({"jobId": job["id"], "scriptId": job["script_id"]}, "Import started", 202)

@bp.get("/api/scripts/import/<job_id>")
def get_import(job_id):
    if (e := _login()): return e
    job = _job(job_id)
    return success_response(public_job_payload(job)) if job else error_response("Import job not found", 404, "Not found")

@bp.get("/api/scripts/import/<job_id>/stream")
def stream_import(job_id):
    if (e := _login()): return e
    if not _job(job_id): return error_response("Import job not found", 404, "Not found")
    def events():
        last = None
        while True:
            job = _job(job_id)
            if not job: break
            marker = job.get("updated_at")
            if marker != last:
                last = marker; yield f"event: progress\ndata: {json.dumps(public_job_payload(job), ensure_ascii=False)}\n\n"
            if job.get("status") in {"done", "failed", "cancelled", "published"}: break
            time.sleep(1)
    return Response(events(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@bp.post("/api/scripts/import/<job_id>/cancel")
def cancel_import(job_id):
    if (e := _login()): return e
    if not _job(job_id): return error_response("Import job not found", 404, "Not found")
    return success_response(public_job_payload(_store().request_cancel(job_id)), "Cancellation requested")

@bp.post("/api/scripts/import/<job_id>/retry")
def retry_import(job_id):
    if (e := _login()): return e
    job = _job(job_id)
    if not job: return error_response("Import job not found", 404, "Not found")
    stage = (request.get_json(silent=True) or {}).get("stage") or job.get("failed_stage") or "parsing"
    _store().update(job_id, status="pending", retry_count=int(job.get("retry_count", 0)) + 1, error=None)
    submit_import_job(current_app._get_current_object(), job_id, start_stage=stage)
    return success_response(public_job_payload(_store().get(job_id)), "Retry started")

@bp.put("/api/scripts/import/<job_id>/preview")
def save_preview(job_id):
    if (e := _login()): return e
    if not _job(job_id): return error_response("Import job not found", 404, "Not found")
    payload = request.get_json(silent=True) or {}; _store().save_intermediate(job_id, "preview", payload); _store().update(job_id, preview=payload)
    return success_response(payload, "Preview saved")

@bp.post("/api/scripts/<int:script_id>/publish")
def publish_import(script_id):
    if (e := _login()): return e
    payload = request.get_json(silent=True) or {}; job = _job(str(payload.get("jobId", "")))
    if not job or int(job.get("script_id", 0)) != script_id: return error_response("Import job not found", 404, "Not found")
    scenario = job.get("preview") or _store().load_intermediate(job["id"], "preview", {})
    scenario["id"] = script_id; scenario["scenario_version"] = str(job.get("target_version") or "1.0.0"); scenario["owner_id"] = session["user_id"]
    from trpg_server.settings import SCENARIOS_DIR
    descriptor = save_scenario_record(SCENARIOS_DIR, scenario)
    persist_knowledge_index(
        descriptor,
        load_scenario_record(descriptor, SCENARIOS_DIR),
        vector_store=current_app.extensions.get("vector_store"),
        embedding_provider=current_app.extensions.get("embedding_provider"),
    )
    _store().update(job["id"], status="published", progress=100)
    return success_response(load_scenario_record(descriptor, SCENARIOS_DIR), "Published", 201)

@bp.get("/api/scripts/<int:script_id>/versions")
def versions(script_id):
    from trpg_server.settings import SCENARIOS_DIR
    descriptor = next((p for p in scenario_descriptor_paths(SCENARIOS_DIR) if str(load_scenario_record(p, SCENARIOS_DIR).get("id")) == str(script_id)), None)
    if not descriptor: return error_response("Scenario not found", 404, "Not found")
    values = []
    for p in sorted((descriptor.parent / "versions").glob("*.json")):
        data = load_scenario_record(p, SCENARIOS_DIR); values.append({"version": p.stem, "created_at": data.get("updatedAt") or data.get("createdAt"), "card_count": len(data.get("modules", []))})
    return success_response(values)

@bp.post("/api/scripts/<int:script_id>/search")
def script_search(script_id):
    if (e := _login()): return e
    data = request.get_json(silent=True) or {}; return success_response(KnowledgeBaseService(rooms_dir=current_app.config.get("ROOMS_DIR"), scenarios_dir=current_app.config.get("SCENARIOS_DIR"), vector_store=current_app.extensions.get("vector_store"), embedding_provider=current_app.extensions.get("embedding_provider")).search(str(data.get("roomId", "")), str(data.get("query", "")), top_k=data.get("topK", 5)))
