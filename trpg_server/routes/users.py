import logging

from flask import Blueprint, request

from trpg_server.responses import error_response, success_response
from trpg_server.security import get_user_manager, require_permission

bp = Blueprint("users", __name__)
logger = logging.getLogger(__name__)


def _public_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
        "last_login": user["last_login"],
        "status": user["status"],
    }


@bp.route("/api/users", methods=["GET"])
@require_permission("ADMIN")
def get_users():
    try:
        users = [_public_user(user) for user in get_user_manager().get_all_users()]
        logger.info("Users listed count=%s", len(users))
        return success_response(users, "Users loaded successfully")
    except Exception as exc:
        logger.exception("Failed to list users")
        return error_response("Failed to load users", 500, str(exc))


@bp.route("/api/users/<int:user_id>/role", methods=["PUT"])
@require_permission("ADMIN")
def update_user_role(user_id):
    try:
        role_data = request.get_json(silent=True)
        if not role_data or "role" not in role_data:
            return error_response("Please provide role data", 400, "No data")

        role = role_data["role"]
        if role not in {"OWNER", "ADMIN", "USER"}:
            return error_response(
                "Role must be OWNER, ADMIN, or USER",
                400,
                "Invalid role",
            )

        success, message = get_user_manager().update_user_role(user_id, role)
        if not success:
            return error_response(message, 404, message)

        logger.info("User role updated user_id=%s role=%s", user_id, role)
        return success_response(message=message)
    except Exception as exc:
        logger.exception("Failed to update user role: %s", user_id)
        return error_response("Failed to update user role", 500, str(exc))


@bp.route("/api/users/<int:user_id>/status", methods=["PUT"])
@require_permission("ADMIN")
def update_user_status(user_id):
    try:
        status_data = request.get_json(silent=True)
        if not status_data or "status" not in status_data:
            return error_response("Please provide status data", 400, "No data")

        status = status_data["status"]
        if status not in {"active", "inactive", "banned"}:
            return error_response(
                "Status must be active, inactive, or banned",
                400,
                "Invalid status",
            )

        success, message = get_user_manager().update_user_status(user_id, status)
        if not success:
            return error_response(message, 404, message)

        logger.info("User status updated user_id=%s status=%s", user_id, status)
        return success_response(message=message)
    except Exception as exc:
        logger.exception("Failed to update user status: %s", user_id)
        return error_response("Failed to update user status", 500, str(exc))


@bp.route("/api/user/ip/config", methods=["GET"])
def get_ip_config():
    try:
        ip_address = request.remote_addr
        manager = get_user_manager()
        config = manager.get_ip_config(ip_address)
        if not config:
            manager.create_ip_config(ip_address)
            config = manager.get_ip_config(ip_address)

        return success_response(config, "IP config loaded successfully")
    except Exception as exc:
        logger.exception("Failed to get IP config")
        return error_response("Failed to get IP config", 500, str(exc))


@bp.route("/api/user/ip/config", methods=["POST"])
def update_ip_config():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return error_response("Please provide config data", 400, "No data")

        ip_address = request.remote_addr
        manager = get_user_manager()
        if not manager.update_ip_config(ip_address, config_data):
            return error_response("IP config update failed", 500, "Update failed")

        updated_config = manager.get_ip_config(ip_address)
        return success_response(updated_config, "IP config updated successfully")
    except Exception as exc:
        logger.exception("Failed to update IP config")
        return error_response("Failed to update IP config", 500, str(exc))


@bp.route("/api/admin/ip/configs", methods=["GET"])
@require_permission("ADMIN")
def get_all_ip_configs():
    try:
        configs = get_user_manager().get_all_ip_configs()
        logger.info("Admin IP configs listed count=%s", len(configs))
        return success_response(configs, "IP configs loaded successfully")
    except Exception as exc:
        logger.exception("Failed to list IP configs")
        return error_response("Failed to list IP configs", 500, str(exc))
