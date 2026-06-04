import logging

from flask import Blueprint, jsonify, request

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
        return jsonify(
            {
                "success": True,
                "data": users,
                "message": "Users loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to list users")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to load users",
                }
            ),
            500,
        )


@bp.route("/api/users/<int:user_id>/role", methods=["PUT"])
@require_permission("ADMIN")
def update_user_role(user_id):
    try:
        role_data = request.get_json(silent=True)
        if not role_data or "role" not in role_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide role data",
                    }
                ),
                400,
            )

        role = role_data["role"]
        if role not in {"OWNER", "ADMIN", "USER"}:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid role",
                        "message": "Role must be OWNER, ADMIN, or USER",
                    }
                ),
                400,
            )

        success, message = get_user_manager().update_user_role(user_id, role)
        if not success:
            return jsonify({"success": False, "error": message, "message": message}), 404

        logger.info("User role updated user_id=%s role=%s", user_id, role)
        return jsonify({"success": True, "message": message})
    except Exception as exc:
        logger.exception("Failed to update user role: %s", user_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to update user role",
                }
            ),
            500,
        )


@bp.route("/api/users/<int:user_id>/status", methods=["PUT"])
@require_permission("ADMIN")
def update_user_status(user_id):
    try:
        status_data = request.get_json(silent=True)
        if not status_data or "status" not in status_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide status data",
                    }
                ),
                400,
            )

        status = status_data["status"]
        if status not in {"active", "inactive", "banned"}:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid status",
                        "message": "Status must be active, inactive, or banned",
                    }
                ),
                400,
            )

        success, message = get_user_manager().update_user_status(user_id, status)
        if not success:
            return jsonify({"success": False, "error": message, "message": message}), 404

        logger.info("User status updated user_id=%s status=%s", user_id, status)
        return jsonify({"success": True, "message": message})
    except Exception as exc:
        logger.exception("Failed to update user status: %s", user_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to update user status",
                }
            ),
            500,
        )


@bp.route("/api/user/ip/config", methods=["GET"])
def get_ip_config():
    try:
        ip_address = request.remote_addr
        manager = get_user_manager()
        config = manager.get_ip_config(ip_address)
        if not config:
            manager.create_ip_config(ip_address)
            config = manager.get_ip_config(ip_address)

        return jsonify(
            {
                "success": True,
                "data": config,
                "message": "IP config loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to get IP config")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to get IP config",
                }
            ),
            500,
        )


@bp.route("/api/user/ip/config", methods=["POST"])
def update_ip_config():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide config data",
                    }
                ),
                400,
            )

        ip_address = request.remote_addr
        manager = get_user_manager()
        if not manager.update_ip_config(ip_address, config_data):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Update failed",
                        "message": "IP config update failed",
                    }
                ),
                500,
            )

        updated_config = manager.get_ip_config(ip_address)
        return jsonify(
            {
                "success": True,
                "data": updated_config,
                "message": "IP config updated successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to update IP config")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to update IP config",
                }
            ),
            500,
        )


@bp.route("/api/admin/ip/configs", methods=["GET"])
@require_permission("ADMIN")
def get_all_ip_configs():
    try:
        configs = get_user_manager().get_all_ip_configs()
        logger.info("Admin IP configs listed count=%s", len(configs))
        return jsonify(
            {
                "success": True,
                "data": configs,
                "message": "IP configs loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to list IP configs")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to list IP configs",
                }
            ),
            500,
        )
