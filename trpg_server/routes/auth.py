import logging
import time
from datetime import timedelta

from flask import Blueprint, current_app, jsonify, request, session

from trpg_server.security import is_allowed_upload, safe_join
from trpg_server.settings import AVATARS_DIR
from user_manager import user_manager

bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

_allowed_avatar_extensions = {"png", "jpg", "jpeg", "gif"}


def _get_user_manager():
    return current_app.config.get("USER_MANAGER", user_manager)


def _user_payload(user):
    return {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "email": user.get("email", ""),
        "avatar": user.get("avatar", "https://via.placeholder.com/40"),
    }


@bp.route("/api/auth/register", methods=["POST"])
def register():
    try:
        ip_address = request.remote_addr
        user_data = request.get_json(silent=True)
        if not user_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide registration data",
                    }
                ),
                400,
            )

        username = user_data.get("username")
        password = user_data.get("password")
        email = user_data.get("email")
        if not username or not password or not email:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Incomplete data",
                        "message": "Please provide username, password, and email",
                    }
                ),
                400,
            )

        success, message = _get_user_manager().register(
            username,
            password,
            email,
            ip_address,
        )
        if not success:
            logger.info("User registration failed username=%s reason=%s", username, message)
            return jsonify({"success": False, "error": message, "message": message}), 400

        logger.info("User registered username=%s email=%s ip=%s", username, email, ip_address)
        return jsonify({"success": True, "message": message}), 201
    except Exception as exc:
        logger.exception("Failed to register user")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Registration failed",
                }
            ),
            500,
        )


@bp.route("/api/auth/login", methods=["POST"])
def login():
    try:
        ip_address = request.remote_addr
        login_data = request.get_json(silent=True)
        if not login_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide login data",
                    }
                ),
                400,
            )

        username = login_data.get("username")
        password = login_data.get("password")
        auto_login = login_data.get("auto_login", False)
        if not username or not password:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Incomplete data",
                        "message": "Please provide username and password",
                    }
                ),
                400,
            )

        success, message, user = _get_user_manager().login(username, password, ip_address)
        if not success:
            logger.info("User login failed username=%s ip=%s reason=%s", username, ip_address, message)
            return jsonify({"success": False, "error": message, "message": message}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        if auto_login:
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(days=7)

        logger.info("User logged in username=%s user_id=%s ip=%s", username, user["id"], ip_address)
        return jsonify(
            {
                "success": True,
                "data": _user_payload(user),
                "message": message,
            }
        )
    except Exception as exc:
        logger.exception("Failed to login user")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Login failed",
                }
            ),
            500,
        )


@bp.route("/api/auth/logout", methods=["POST"])
def logout():
    try:
        if "user_id" not in session:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Not logged in",
                        "message": "You are not logged in",
                    }
                ),
                401,
            )

        username = session.get("username")
        session.clear()
        logger.info("User logged out username=%s", username)
        return jsonify({"success": True, "message": "Logged out successfully"})
    except Exception as exc:
        logger.exception("Failed to logout user")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Logout failed",
                }
            ),
            500,
        )


@bp.route("/api/auth/status", methods=["GET"])
def get_auth_status():
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        user = _get_user_manager().get_user_by_id(session["user_id"])
        if not user:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "User not found",
                        "message": "User not found",
                    }
                ),
                404,
            )

        logger.info(
            "Auth status user_id=%s username=%s ip=%s",
            session["user_id"],
            session["username"],
            request.remote_addr,
        )
        return jsonify(
            {
                "success": True,
                "data": _user_payload(user),
                "message": "Logged in",
            }
        )
    except Exception as exc:
        logger.exception("Failed to get auth status")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to get auth status",
                }
            ),
            500,
        )


@bp.route("/api/auth/update", methods=["POST"])
def update_user():
    try:
        if "user_id" not in session:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Not logged in",
                        "message": "Please login first",
                    }
                ),
                401,
            )

        manager = _get_user_manager()
        user_id = session["user_id"]
        user = manager.get_user_by_id(user_id)
        if not user:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "User not found",
                        "message": "User not found",
                    }
                ),
                404,
            )

        username = request.form.get("username")
        nickname = request.form.get("nickname")
        email = request.form.get("email") or user.get("email", "")
        password = request.form.get("password")
        if not username:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Incomplete data",
                        "message": "Please provide username",
                    }
                ),
                400,
            )

        avatar_path = user.get("avatar", "https://via.placeholder.com/40")
        if "avatar" in request.files:
            avatar_path = _save_avatar(request.files["avatar"], user_id)

        user["username"] = username
        user["nickname"] = nickname
        user["email"] = email
        user["avatar"] = avatar_path
        if password:
            user["password"] = manager._hash_password(password)

        if not manager._save_users():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to save data",
                        "message": "Failed to save user data",
                    }
                ),
                500,
            )

        session["username"] = username
        logger.info("User profile updated user_id=%s username=%s", user_id, username)
        return jsonify(
            {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "username": username,
                    "nickname": nickname,
                    "email": email,
                    "avatar": avatar_path,
                },
                "message": "Updated successfully",
            }
        )
    except ValueError as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": str(exc),
                }
            ),
            400,
        )
    except Exception as exc:
        logger.exception("Failed to update user")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": f"Update failed: {exc}",
                }
            ),
            500,
        )


def _save_avatar(avatar, user_id):
    if not is_allowed_upload(avatar.filename or "", _allowed_avatar_extensions):
        raise ValueError("Please upload an image file")

    if (avatar.content_length or 0) > 2 * 1024 * 1024:
        raise ValueError("Avatar file size must not exceed 2MB")

    filename = f"{user_id}_{int(time.time())}_{avatar.filename}"
    file_path = safe_join(AVATARS_DIR, filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    avatar.save(file_path)
    return f"/assets/avatars/{filename}"
