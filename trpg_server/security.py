from functools import wraps
from pathlib import Path

from flask import current_app, jsonify, session


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


def get_user_manager():
    from user_manager import user_manager

    return current_app.config.get("USER_MANAGER", user_manager)


def require_permission(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
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

            manager = get_user_manager()
            if not manager.check_permission(session["user_id"], required_role):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Permission denied",
                            "message": "Permission denied",
                        }
                    ),
                    403,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator
