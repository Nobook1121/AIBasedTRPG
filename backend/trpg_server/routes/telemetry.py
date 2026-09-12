from __future__ import annotations

from flask import Blueprint, current_app, request

from trpg_server.agents.telemetry import load_daily_ai_usage
from trpg_server.responses import success_response
from trpg_server.security import require_permission_node
from trpg_server.settings import LOGS_DIR


bp = Blueprint("telemetry", __name__)


@bp.route("/api/telemetry/ai/daily", methods=["GET"])
@require_permission_node("settings.ai_models")
def get_daily_ai_usage():
    log_dir = current_app.config.get("LOGS_DIR", LOGS_DIR)
    day = request.args.get("day") or None
    return success_response(data=load_daily_ai_usage(log_dir, day=day))
