import logging

from flask import Blueprint, current_app, request, session

from trpg_server.responses import error_response, success_response
from trpg_server.security import get_user_manager, require_permission
from trpg_server.users.smtp import (
    admin_auth_settings,
    get_auth_settings,
    update_auth_settings,
)

bp = Blueprint("users", __name__)
logger = logging.getLogger(__name__)

ALLOWED_PRESENCE = {"online", "dnd", "invisible"}


def _auth_settings_db():
    manager = get_user_manager()
    return getattr(manager, "db", None)


def _auth_settings_fallback():
    return current_app.config.setdefault("AUTH_SETTINGS", {})


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


def _profile_payload(user):
    return {
        "user_id": user.get("id", user.get("user_id")),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "USER"),
        "avatar": user.get("avatar", "/assets/avatars/default.jpg"),
        "nickname": user.get("nickname") or user.get("username", ""),
        "presence": user.get("presence", "online"),
        "two_factor_enabled": user.get("two_factor_enabled", False),
    }


def _require_current_user():
    if "user_id" not in session:
        return None, error_response("Please login first", 401, "Not logged in")

    user = get_user_manager().get_user_by_id(session["user_id"])
    if not user:
        return None, error_response("User not found", 404, "User not found")

    return user, None


@bp.route("/api/users", methods=["GET"])
@require_permission("ADMIN")
def get_users():
    try:
        users = [_public_user(user) for user in get_user_manager().get_all_users()]
        logger.debug("Users listed count=%s", len(users))
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

        logger.debug("User role updated user_id=%s role=%s", user_id, role)
        return success_response(message=message)
    except Exception as exc:
        logger.exception("Failed to update user role: %s", user_id)
        return error_response("Failed to update user role", 500, str(exc))


@bp.route("/api/user/profile", methods=["GET"])
def get_current_user_profile():
    try:
        user, error = _require_current_user()
        if error:
            return error

        return success_response(_profile_payload(user), "Profile loaded successfully")
    except Exception as exc:
        logger.exception("Failed to get user profile")
        return error_response("Failed to get user profile", 500, str(exc))


@bp.route("/api/user/profile", methods=["PUT"])
def update_current_user_profile():
    try:
        user, error = _require_current_user()
        if error:
            return error

        profile_data = request.get_json(silent=True)
        if not profile_data:
            return error_response("Please provide profile data", 400, "No data")

        username = profile_data.get("username", user.get("username", ""))
        email = profile_data.get("email", user.get("email", ""))
        nickname = profile_data.get(
            "nickname",
            user.get("nickname") or user.get("username", ""),
        )
        avatar = profile_data.get("avatar", user.get("avatar"))

        manager = get_user_manager()
        if hasattr(manager, "update_profile"):
            success, message = manager.update_profile(
                session["user_id"],
                username=username,
                email=email,
                nickname=nickname,
                avatar=avatar,
            )
            if not success:
                return error_response(message, 400, message)
            updated_user = manager.get_user_by_id(session["user_id"])
        else:
            original_user = dict(user)
            user["username"] = username
            user["email"] = email
            user["nickname"] = nickname
            user["avatar"] = avatar
            try:
                saved = manager._save_users()
            except Exception:
                user.clear()
                user.update(original_user)
                raise
            if not saved:
                user.clear()
                user.update(original_user)
                return error_response("Failed to save user data", 500, "Failed to save data")
            updated_user = user

        session["username"] = username
        return success_response(_profile_payload(updated_user), "Profile updated")
    except Exception as exc:
        logger.exception("Failed to update user profile")
        return error_response("Failed to update user profile", 500, str(exc))


@bp.route("/api/user/presence", methods=["PUT"])
def update_current_user_presence():
    try:
        user, error = _require_current_user()
        if error:
            return error

        presence_data = request.get_json(silent=True)
        if not presence_data or "presence" not in presence_data:
            return error_response("Please provide presence data", 400, "No data")

        presence = presence_data["presence"]
        if presence not in ALLOWED_PRESENCE:
            return error_response("Invalid presence", 400, "Invalid presence")

        manager = get_user_manager()
        if hasattr(manager, "update_presence"):
            success, message = manager.update_presence(session["user_id"], presence)
            if not success:
                return error_response(message, 400, message)
            updated_user = manager.get_user_by_id(session["user_id"])
        else:
            original_user = dict(user)
            user["presence"] = presence
            try:
                saved = manager._save_users()
            except Exception:
                user.clear()
                user.update(original_user)
                raise
            if not saved:
                user.clear()
                user.update(original_user)
                return error_response("Failed to save user data", 500, "Failed to save data")
            updated_user = user

        return success_response(_profile_payload(updated_user), "Presence updated")
    except Exception as exc:
        logger.exception("Failed to update user presence")
        return error_response("Failed to update user presence", 500, str(exc))


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

        logger.debug("User status updated user_id=%s status=%s", user_id, status)
        return success_response(message=message)
    except Exception as exc:
        logger.exception("Failed to update user status: %s", user_id)
        return error_response("Failed to update user status", 500, str(exc))


@bp.route("/api/admin/auth/settings", methods=["GET"])
@require_permission("ADMIN")
def get_admin_auth_settings():
    try:
        settings = get_auth_settings(_auth_settings_db(), _auth_settings_fallback())
        return success_response(admin_auth_settings(settings), "Auth settings loaded")
    except Exception as exc:
        logger.exception("Failed to get admin auth settings")
        return error_response("Failed to get auth settings", 500, str(exc))


@bp.route("/api/admin/auth/settings", methods=["PUT"])
@require_permission("ADMIN")
def update_admin_auth_settings():
    try:
        settings_data = request.get_json(silent=True)
        if not settings_data:
            return error_response("Please provide auth settings data", 400, "No data")

        settings = update_auth_settings(
            settings_data,
            _auth_settings_db(),
            _auth_settings_fallback(),
        )
        logger.info("Admin auth settings updated user_id=%s", session.get("user_id"))
        return success_response(admin_auth_settings(settings), "Auth settings updated")
    except ValueError as exc:
        return error_response(str(exc), 400, str(exc))
    except Exception as exc:
        logger.exception("Failed to update admin auth settings")
        return error_response("Failed to update auth settings", 500, str(exc))


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
        logger.debug("Admin IP configs listed count=%s", len(configs))
        return success_response(configs, "IP configs loaded successfully")
    except Exception as exc:
        logger.exception("Failed to list IP configs")
        return error_response("Failed to list IP configs", 500, str(exc))
