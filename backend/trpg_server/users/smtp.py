from __future__ import annotations

from typing import Any


BOOLEAN_FIELDS = {
    "email_verification_enabled",
    "password_reset_enabled",
    "two_factor_enabled",
    "smtp_enabled",
}
SMTP_FIELDS = {
    "smtp_host",
    "smtp_port",
    "smtp_username",
    "smtp_password",
    "smtp_from",
}
SETTING_FIELDS = BOOLEAN_FIELDS | SMTP_FIELDS


DEFAULT_AUTH_SETTINGS = {
    "email_verification_enabled": False,
    "password_reset_enabled": False,
    "two_factor_enabled": False,
    "smtp_enabled": False,
    "smtp_host": None,
    "smtp_port": None,
    "smtp_username": None,
    "smtp_password": None,
    "smtp_from": None,
}


def get_auth_settings(db=None, fallback_store: dict[str, Any] | None = None) -> dict[str, Any]:
    if db is None:
        return _settings_from_fallback(fallback_store)

    with db.connect() as connection:
        _ensure_settings_row(connection)
        row = connection.execute("SELECT * FROM auth_settings WHERE id = 1").fetchone()

    return _row_to_settings(row)


def update_auth_settings(
    updates: dict[str, Any],
    db=None,
    fallback_store: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sanitized = _sanitize_updates(updates)
    if db is None:
        settings = _settings_from_fallback(fallback_store)
        settings.update(sanitized)
        if fallback_store is not None:
            fallback_store.clear()
            fallback_store.update(settings)
        return settings

    if not sanitized:
        return get_auth_settings(db)

    assignments = ", ".join(f"{field} = ?" for field in sanitized)
    values = [_to_storage_value(field, value) for field, value in sanitized.items()]
    values.append(1)
    with db.connect() as connection:
        _ensure_settings_row(connection)
        connection.execute(
            f"""
            UPDATE auth_settings
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )

    return get_auth_settings(db)


def public_auth_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "email_verification_enabled": bool(settings["email_verification_enabled"]),
        "password_reset_enabled": bool(settings["password_reset_enabled"]),
        "two_factor_enabled": bool(settings["two_factor_enabled"]),
    }


def admin_auth_settings(settings: dict[str, Any]) -> dict[str, Any]:
    payload = dict(public_auth_settings(settings))
    payload.update(
        {
            "smtp_enabled": bool(settings["smtp_enabled"]),
            "smtp_configured": bool(settings.get("smtp_host") and settings.get("smtp_from")),
            "smtp_host": settings.get("smtp_host"),
            "smtp_port": settings.get("smtp_port"),
            "smtp_username": settings.get("smtp_username"),
            "smtp_from": settings.get("smtp_from"),
            "smtp_password_configured": bool(settings.get("smtp_password")),
        }
    )
    return payload


def send_mail(settings: dict[str, Any], to_address: str, subject: str, body: str) -> bool:
    if not settings.get("smtp_enabled"):
        raise RuntimeError("SMTP is disabled")
    if not settings.get("smtp_host") or not settings.get("smtp_from"):
        raise RuntimeError("SMTP is not configured")
    return False


def _settings_from_fallback(fallback_store: dict[str, Any] | None) -> dict[str, Any]:
    settings = dict(DEFAULT_AUTH_SETTINGS)
    if fallback_store:
        settings.update({key: fallback_store.get(key) for key in SETTING_FIELDS if key in fallback_store})
    return settings


def _ensure_settings_row(connection) -> None:
    connection.execute(
        """
        INSERT INTO auth_settings (id)
        SELECT 1
        WHERE NOT EXISTS (SELECT 1 FROM auth_settings WHERE id = 1)
        """
    )


def _row_to_settings(row) -> dict[str, Any]:
    settings = dict(DEFAULT_AUTH_SETTINGS)
    for field in SETTING_FIELDS:
        value = row[field]
        if field in BOOLEAN_FIELDS:
            value = bool(value)
        settings[field] = value
    return settings


def _sanitize_updates(updates: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for field, value in updates.items():
        if field not in SETTING_FIELDS:
            continue
        if field in BOOLEAN_FIELDS:
            sanitized[field] = _sanitize_boolean(field, value)
        elif field == "smtp_port":
            sanitized[field] = _sanitize_port(value)
        else:
            sanitized[field] = str(value).strip() if value not in (None, "") else None
    return sanitized


def _sanitize_boolean(field: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field} must be a boolean")


def _sanitize_port(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("SMTP port must be an integer")
    if isinstance(value, int):
        port = value
    elif isinstance(value, str) and value.isdigit():
        port = int(value)
    else:
        raise ValueError("SMTP port must be an integer")
    if port < 1 or port > 65535:
        raise ValueError("SMTP port must be between 1 and 65535")
    return port


def _to_storage_value(field: str, value: Any) -> Any:
    if field in BOOLEAN_FIELDS:
        return 1 if value else 0
    return value
