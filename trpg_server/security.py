from functools import wraps
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from uuid import uuid4

from flask import current_app, request, session

from trpg_server.responses import error_response

ACTIVE_SESSION_REGISTRY_KEY = "ACTIVE_USER_SESSIONS"
SESSION_TOKEN_KEY = "session_token"
WINDOWS_RESERVED_FILENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def safe_join(base, *parts):
    base_path = Path(base).resolve()
    target_path = base_path.joinpath(*parts).resolve()

    try:
        target_path.relative_to(base_path)
    except ValueError as exc:
        raise ValueError("Unsafe path") from exc

    return target_path


def is_allowed_upload(filename, allowed_extensions):
    suffix = Path(filename).suffix
    if not suffix:
        return False

    suffix = suffix.lower().lstrip(".")
    return suffix in {extension.lower().lstrip(".") for extension in allowed_extensions}


def normalize_filename(filename, fallback="file"):
    raw_name = str(filename or "").replace("\\", "/")
    basename = PurePosixPath(raw_name).name.strip()
    if not basename:
        basename = fallback

    normalized = "".join(
        character if character.isalnum() or character in {" ", ".", "-", "_"} else "_"
        for character in basename
    ).strip(" .")
    if not normalized:
        normalized = fallback

    if "." in normalized:
        stem, suffix = normalized.rsplit(".", 1)
        if stem.upper() in WINDOWS_RESERVED_FILENAMES:
            stem = f"_{stem}"
        normalized = f"{stem}.{suffix}"
    elif normalized.upper() in WINDOWS_RESERVED_FILENAMES:
        normalized = f"_{normalized}"

    return normalized[:160]


def build_public_asset_url(prefix, filename):
    normalized_prefix = "/" + str(prefix or "").strip("/")
    return f"{normalized_prefix}/{quote(normalize_filename(filename), safe='')}"


def get_user_manager():
    from user_manager import user_manager

    return current_app.config.get("USER_MANAGER", user_manager)


def issue_session_token(user_id):
    token = uuid4().hex
    active_sessions = current_app.config.setdefault(ACTIVE_SESSION_REGISTRY_KEY, {})
    active_sessions[str(user_id)] = token
    return token


def clear_session_token(user_id, token):
    active_sessions = current_app.config.setdefault(ACTIVE_SESSION_REGISTRY_KEY, {})
    user_key = str(user_id)
    if active_sessions.get(user_key) == token:
        active_sessions.pop(user_key, None)


def register_session_guard(app):
    @app.before_request
    def _enforce_single_session():
        if not request.path.startswith("/api/"):
            return None
        if request.path in {"/api/auth/login", "/api/auth/register"}:
            return None
        if "user_id" not in session:
            return None

        active_sessions = current_app.config.setdefault(ACTIVE_SESSION_REGISTRY_KEY, {})
        active_token = active_sessions.get(str(session["user_id"]))
        if active_token and session.get(SESSION_TOKEN_KEY) != active_token:
            session.clear()
            return error_response("Session expired", 401, "Session expired")

        return None


def require_permission(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return error_response("Please login first", 401, "Not logged in")

            active_sessions = current_app.config.setdefault(ACTIVE_SESSION_REGISTRY_KEY, {})
            active_token = active_sessions.get(str(session["user_id"]))
            if active_token and session.get(SESSION_TOKEN_KEY) != active_token:
                session.clear()
                return error_response("Session expired", 401, "Session expired")

            manager = get_user_manager()
            if not manager.check_permission(session["user_id"], required_role):
                return error_response("Permission denied", 403, "Permission denied")

            return func(*args, **kwargs)

        return wrapper

    return decorator
