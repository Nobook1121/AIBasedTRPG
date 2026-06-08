import logging
import time
from datetime import timedelta

from flask import Blueprint, current_app, request, session

from trpg_server.responses import error_response, success_response
from trpg_server.security import (
    SESSION_TOKEN_KEY,
    build_public_asset_url,
    clear_session_token,
    is_allowed_upload,
    issue_session_token,
    normalize_filename,
    safe_join,
)
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
        "avatar": user.get("avatar", "/assets/avatars/default.jpg"),
    }


@bp.route("/api/auth/register", methods=["POST"])
def register():
    try:
        ip_address = request.remote_addr
        user_data = request.get_json(silent=True)
        if not user_data:
            return error_response("Please provide registration data", 400, "No data")

        username = user_data.get("username")
        password = user_data.get("password")
        email = user_data.get("email")
        if not username or not password or not email:
            return error_response(
                "Please provide username, password, and email",
                400,
                "Incomplete data",
            )

        success, message = _get_user_manager().register(
            username,
            password,
            email,
            ip_address,
        )
        if not success:
            logger.debug("User registration failed username=%s reason=%s", username, message)
            return error_response(message, 400, message)

        logger.debug("User registered username=%s email=%s ip=%s", username, email, ip_address)
        return success_response(message=message, status=201)
    except Exception as exc:
        logger.exception("Failed to register user")
        return error_response("Registration failed", 500, str(exc))


@bp.route("/api/auth/login", methods=["POST"])
def login():
    try:
        ip_address = request.remote_addr
        login_data = request.get_json(silent=True)
        if not login_data:
            return error_response("Please provide login data", 400, "No data")

        username = login_data.get("username")
        password = login_data.get("password")
        auto_login = login_data.get("auto_login", False)
        if not username or not password:
            return error_response(
                "Please provide username and password",
                400,
                "Incomplete data",
            )

        success, message, user = _get_user_manager().login(username, password, ip_address)
        if not success:
            logger.info("User login failed username=%s ip=%s reason=%s", username, ip_address, message)
            return error_response(message, 401, message)

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session[SESSION_TOKEN_KEY] = issue_session_token(user["id"])
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(days=7)

        logger.info("User logged in username=%s user_id=%s ip=%s", username, user["id"], ip_address)
        return success_response(_user_payload(user), message)
    except Exception as exc:
        logger.exception("Failed to login user")
        return error_response("Login failed", 500, str(exc))


@bp.route("/api/auth/logout", methods=["POST"])
def logout():
    try:
        if "user_id" not in session:
            return error_response("You are not logged in", 401, "Not logged in")

        username = session.get("username")
        user_id = session.get("user_id")
        session_token = session.get(SESSION_TOKEN_KEY)
        session.clear()
        clear_session_token(user_id, session_token)
        logger.debug("User logged out username=%s", username)
        return success_response(message="Logged out successfully")
    except Exception as exc:
        logger.exception("Failed to logout user")
        return error_response("Logout failed", 500, str(exc))


@bp.route("/api/auth/status", methods=["GET"])
def get_auth_status():
    try:
        if "user_id" not in session:
            return error_response("Not logged in", 401)

        user = _get_user_manager().get_user_by_id(session["user_id"])
        if not user:
            return error_response("User not found", 404, "User not found")

        logger.debug(
            "Auth status user_id=%s username=%s ip=%s",
            session["user_id"],
            session["username"],
            request.remote_addr,
        )
        return success_response(_user_payload(user), "Logged in")
    except Exception as exc:
        logger.exception("Failed to get auth status")
        return error_response("Failed to get auth status", 500, str(exc))


@bp.route("/api/auth/update", methods=["POST"])
def update_user():
    try:
        if "user_id" not in session:
            return error_response("Please login first", 401, "Not logged in")

        manager = _get_user_manager()
        user_id = session["user_id"]
        user = manager.get_user_by_id(user_id)
        if not user:
            return error_response("User not found", 404, "User not found")

        username = request.form.get("username")
        nickname = request.form.get("nickname")
        email = request.form.get("email") or user.get("email", "")
        password = request.form.get("password")
        if not username:
            return error_response("Please provide username", 400, "Incomplete data")

        avatar_path = user.get("avatar", "/assets/avatars/default.jpg")
        if "avatar" in request.files:
            avatar_path = _save_avatar(request.files["avatar"], user_id)

        if hasattr(manager, "update_profile"):
            success, message = manager.update_profile(
                user_id,
                username=username,
                email=email,
                nickname=nickname,
                avatar=avatar_path,
                password=password,
            )
            if not success:
                return error_response(message, 400, message)
            user = manager.get_user_by_id(user_id)
        else:
            user["username"] = username
            user["nickname"] = nickname
            user["email"] = email
            user["avatar"] = avatar_path
            if password:
                user["password"] = manager._hash_password(password)

            if not manager._save_users():
                return error_response("Failed to save user data", 500, "Failed to save data")

        session["username"] = username
        logger.debug("User profile updated user_id=%s username=%s", user_id, username)
        return success_response(
            {
                "user_id": user_id,
                "username": username,
                "nickname": nickname,
                "email": email,
                "avatar": avatar_path,
            },
            "Updated successfully",
        )
    except ValueError as exc:
        return error_response(str(exc), 400, str(exc))
    except Exception as exc:
        logger.exception("Failed to update user")
        return error_response(f"Update failed: {exc}", 500, str(exc))


def _save_avatar(avatar, user_id):
    if not is_allowed_upload(avatar.filename or "", _allowed_avatar_extensions):
        raise ValueError("Please upload an image file")

    if (avatar.content_length or 0) > 2 * 1024 * 1024:
        raise ValueError("Avatar file size must not exceed 2MB")

    uploaded_filename = normalize_filename(avatar.filename or "avatar")
    filename = f"{user_id}_{int(time.time())}_{uploaded_filename}"
    file_path = safe_join(AVATARS_DIR, filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    avatar.save(file_path)
    return build_public_asset_url("/assets/avatars", filename)
