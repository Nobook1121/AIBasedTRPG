import inspect
import logging
import time
import uuid
from datetime import timedelta

from flask import Blueprint, current_app, request, session

from trpg_server.logging_config import log_user_action, user_action_text
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
from trpg_server.users.smtp import get_auth_settings, public_auth_settings
from trpg_server.users.tokens import (
    disabled_message,
    email_verification_available,
    password_reset_available,
)
from trpg_server.users.manager import user_manager

bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

_allowed_avatar_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
_allowed_avatar_mime_types = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_avatar_signatures = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
}
_max_avatar_size_bytes = 2 * 1024 * 1024


def _get_user_manager():
    return current_app.config.get("USER_MANAGER", user_manager)


def _auth_settings():
    manager = _get_user_manager()
    return get_auth_settings(
        getattr(manager, "db", None),
        current_app.config.setdefault("AUTH_SETTINGS", {}),
    )


def _user_payload(user):
    return {
        "user_id": user.get("id", user.get("user_id")),
        "username": user.get("username", ""),
        "role": user.get("role", "USER"),
        "email": user.get("email", ""),
        "avatar": user.get("avatar", "/assets/avatars/default.jpg"),
        "nickname": user.get("nickname") or user.get("username", ""),
        "presence": user.get("presence", "online"),
        "two_factor_enabled": user.get("two_factor_enabled", False),
    }


def _register_user(manager, username, password, email, terms_accepted, ip_address):
    register_signature = inspect.signature(manager.register)
    parameters = register_signature.parameters.values()
    supports_terms_accepted = "terms_accepted" in register_signature.parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters
    )
    if supports_terms_accepted:
        return manager.register(
            username,
            password,
            email,
            terms_accepted=terms_accepted,
            ip_address=ip_address,
        )

    return manager.register(username, password, email, ip_address)


@bp.route("/api/auth/register", methods=["POST"])
def register():
    try:
        ip_address = request.remote_addr
        user_data = request.get_json(silent=True)
        if not user_data:
            return error_response("Please provide registration data", 400, "No data")

        username = user_data.get("username")
        password = user_data.get("password")
        confirm_password = user_data.get("confirm_password")
        email = user_data.get("email")
        terms_accepted = user_data.get("terms_accepted") is True
        if not username or not password or not email:
            return error_response(
                "Please provide username, password, and email",
                400,
                "Incomplete data",
            )
        if not terms_accepted:
            return error_response("Terms must be accepted", 400, "Terms must be accepted")
        if password != confirm_password:
            return error_response("Passwords do not match", 400, "Passwords do not match")

        result = _register_user(
            _get_user_manager(),
            username,
            password,
            email,
            terms_accepted,
            ip_address,
        )
        success, message = result[0], result[1]
        if not success:
            logger.debug("User registration failed username=%s reason=%s", username, message)
            return error_response(message, 400, message)

        log_user_action(
            logger,
            user_action_text(username, "注册了账号"),
            邮箱=email,
            IP=ip_address,
        )
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

        identifier = login_data.get("identifier") or login_data.get("username")
        password = login_data.get("password")
        auto_login = login_data.get("auto_login", False)
        if not identifier or not password:
            return error_response(
                "Please provide username and password",
                400,
                "Incomplete data",
            )

        result = _get_user_manager().login(identifier, password, ip_address)
        success, message, user = result[0], result[1], result[2]
        manager_session_token = result[3] if len(result) > 3 else None
        if not success:
            log_user_action(
                logger,
                user_action_text(identifier, "登录失败"),
                IP=ip_address,
                原因=message,
            )
            return error_response(message, 401, message)

        manager = _get_user_manager()
        if hasattr(manager, "is_session_current") and not manager_session_token:
            logger.error(
                "Manager login did not return session token username=%s user_id=%s",
                identifier,
                user["id"],
            )
            return error_response("Login failed", 500, "Session token missing")

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session[SESSION_TOKEN_KEY] = manager_session_token or issue_session_token(user["id"])
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(days=7)

        log_user_action(
            logger,
            user_action_text(user.get("username") or identifier, "登录成功"),
            用户ID=user["id"],
            IP=ip_address,
        )
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
        manager = _get_user_manager()
        revoke_error = None
        try:
            if hasattr(manager, "revoke_session"):
                manager.revoke_session(user_id, session_token)
            else:
                clear_session_token(user_id, session_token)
        except Exception as exc:
            revoke_error = exc
            logger.exception("Failed to revoke session username=%s", username)
        finally:
            session.clear()

        if revoke_error:
            return error_response("Logout failed", 500, str(revoke_error))

        log_user_action(
            logger,
            user_action_text(username, "退出登录"),
            用户ID=user_id,
        )
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
    saved_avatar_file = None
    avatar_persisted = False
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
        if "password" in request.form:
            return error_response(
                "Use /api/auth/password/change to change password",
                400,
                "Use /api/auth/password/change to change password",
            )
        if not username:
            return error_response("Please provide username", 400, "Incomplete data")

        avatar_path = user.get("avatar", "/assets/avatars/default.jpg")
        if "avatar" in request.files:
            avatar_path, saved_avatar_file = _save_avatar(request.files["avatar"], user_id)

        if hasattr(manager, "update_profile"):
            success, message = manager.update_profile(
                user_id,
                username=username,
                email=email,
                nickname=nickname,
                avatar=avatar_path,
            )
            if not success:
                _remove_saved_avatar(saved_avatar_file)
                return error_response(message, 400, message)
            avatar_persisted = True
        else:
            original_user = dict(user)
            user["username"] = username
            user["nickname"] = nickname
            user["email"] = email
            user["avatar"] = avatar_path

            try:
                saved = manager._save_users()
            except Exception:
                user.clear()
                user.update(original_user)
                _remove_saved_avatar(saved_avatar_file)
                raise

            if not saved:
                user.clear()
                user.update(original_user)
                _remove_saved_avatar(saved_avatar_file)
                return error_response("Failed to save user data", 500, "Failed to save data")
            avatar_persisted = True

        session["username"] = username
        log_user_action(
            logger,
            user_action_text(username, "更改了个人资料"),
            用户ID=user_id,
            昵称=nickname,
            邮箱=email,
            更换头像="是" if saved_avatar_file else "否",
        )
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
        if not avatar_persisted:
            _remove_saved_avatar(saved_avatar_file)
        return error_response(str(exc), 400, str(exc))
    except Exception as exc:
        if not avatar_persisted:
            _remove_saved_avatar(saved_avatar_file)
        logger.exception("Failed to update user")
        return error_response(f"Update failed: {exc}", 500, str(exc))


@bp.route("/api/auth/password/change", methods=["POST"])
def change_password():
    try:
        if "user_id" not in session:
            return error_response("Please login first", 401, "Not logged in")

        password_data = request.get_json(silent=True)
        if not password_data:
            return error_response("Please provide password data", 400, "No data")

        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        if not current_password or not new_password:
            return error_response(
                "Please provide current and new password",
                400,
                "Incomplete data",
            )

        manager = _get_user_manager()
        user_id = session["user_id"]
        if hasattr(manager, "change_password"):
            success, message = manager.change_password(
                user_id,
                current_password,
                new_password,
            )
            if not success:
                return error_response(message, 400, message)
            log_user_action(
                logger,
                user_action_text(session.get("username"), "更改了登录密码"),
                用户ID=user_id,
            )
            return success_response(message=message)

        user = manager.get_user_by_id(user_id)
        if not user:
            return error_response("User not found", 404, "User not found")
        stored_password = user.get("password", "")
        if hasattr(manager, "_verify_password"):
            password_matches = manager._verify_password(current_password, stored_password)
        else:
            password_matches = stored_password == current_password
        if not password_matches:
            return error_response(
                "Current password is incorrect",
                400,
                "Current password is incorrect",
            )
        original_user = dict(user)
        user["password"] = manager._hash_password(new_password)
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
        log_user_action(
            logger,
            user_action_text(session.get("username"), "更改了登录密码"),
            用户ID=user_id,
        )
        return success_response(message="Password changed")
    except Exception as exc:
        logger.exception("Failed to change password")
        return error_response("Password change failed", 500, str(exc))


@bp.route("/api/auth/settings", methods=["GET"])
def get_auth_settings_route():
    try:
        return success_response(public_auth_settings(_auth_settings()), "Auth settings loaded")
    except Exception as exc:
        logger.exception("Failed to get auth settings")
        return error_response("Failed to get auth settings", 500, str(exc))


@bp.route("/api/auth/password/forgot", methods=["POST"])
def forgot_password():
    settings = _auth_settings()
    if not password_reset_available(settings):
        logger.info("Password reset request rejected because feature is disabled")
        return error_response(
            disabled_message("Password reset"),
            403,
            "Password reset disabled",
        )

    logger.warning("Password reset requested but SMTP/token delivery is not implemented")
    return error_response("Password reset is not configured", 501, "Not implemented")


@bp.route("/api/auth/password/reset", methods=["POST"])
def reset_password():
    settings = _auth_settings()
    if not password_reset_available(settings):
        return error_response(
            disabled_message("Password reset"),
            403,
            "Password reset disabled",
        )

    return error_response("Password reset is not configured", 501, "Not implemented")


@bp.route("/api/auth/email/verify/request", methods=["POST"])
def request_email_verification():
    settings = _auth_settings()
    if not email_verification_available(settings):
        logger.info("Email verification request rejected because feature is disabled")
        return error_response(
            disabled_message("Email verification"),
            403,
            "Email verification disabled",
        )

    return error_response("Email verification is not configured", 501, "Not implemented")


@bp.route("/api/auth/email/verify/confirm", methods=["POST"])
def confirm_email_verification():
    settings = _auth_settings()
    if not email_verification_available(settings):
        return error_response(
            disabled_message("Email verification"),
            403,
            "Email verification disabled",
        )

    return error_response("Email verification is not configured", 501, "Not implemented")


def _save_avatar(avatar, user_id):
    if not is_allowed_upload(avatar.filename or "", _allowed_avatar_extensions):
        raise ValueError("Please upload an image file")

    content_type = (avatar.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in _allowed_avatar_mime_types:
        raise ValueError("Please upload a PNG, JPEG, GIF, or WebP image")

    avatar_bytes = avatar.stream.read(_max_avatar_size_bytes + 1)
    if len(avatar_bytes) > _max_avatar_size_bytes:
        raise ValueError("Avatar file size must not exceed 2MB")

    if not _avatar_bytes_match_content_type(avatar_bytes, content_type):
        raise ValueError("Please upload a PNG, JPEG, GIF, or WebP image")

    uploaded_filename = normalize_filename(avatar.filename or "avatar")
    filename = f"{user_id}_{int(time.time())}_{uuid.uuid4().hex}_{uploaded_filename}"
    file_path = safe_join(AVATARS_DIR, filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(avatar_bytes)
    return build_public_asset_url("/assets/avatars", filename), file_path


def _remove_saved_avatar(file_path):
    if not file_path:
        return
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Failed to remove orphaned avatar file path=%s", file_path)


def _avatar_bytes_match_content_type(avatar_bytes, content_type):
    if content_type == "image/webp":
        return (
            len(avatar_bytes) >= 12
            and avatar_bytes.startswith(b"RIFF")
            and avatar_bytes[8:12] == b"WEBP"
        )

    return any(
        avatar_bytes.startswith(signature)
        for signature in _avatar_signatures.get(content_type, ())
    )
