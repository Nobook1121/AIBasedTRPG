from __future__ import annotations


def password_reset_available(settings: dict) -> bool:
    return bool(settings.get("password_reset_enabled"))


def email_verification_available(settings: dict) -> bool:
    return bool(settings.get("email_verification_enabled"))


def disabled_message(feature_name: str) -> str:
    return f"{feature_name} is disabled by the administrator"
