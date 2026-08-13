from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (AttributeError, TypeError, ValueError):
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(char.isalpha() for char in password):
        return False, "Password must include a letter"
    if not any(char.isdigit() for char in password):
        return False, "Password must include a number"
    return True, "Password is strong"
