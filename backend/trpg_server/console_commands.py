from __future__ import annotations

from dataclasses import dataclass
import logging
import shlex
import threading
from typing import Any, TextIO

from trpg_server.users.manager import user_manager as default_user_manager

logger = logging.getLogger(__name__)

VALID_ROLES = {"USER", "ADMIN", "OWNER"}


@dataclass
class ConsoleCommandResult:
    ok: bool
    message: str


def execute_console_command(command_line: str, user_manager: Any = default_user_manager) -> ConsoleCommandResult:
    try:
        parts = shlex.split(command_line)
    except ValueError as exc:
        return ConsoleCommandResult(False, f"Invalid command syntax: {exc}")

    if not parts:
        return ConsoleCommandResult(True, "")

    if parts[0] in {"help", "?"}:
        result = ConsoleCommandResult(True, command_help_text())
        logger.info("%s", result.message)
        return result

    if parts[:2] == ["user", "promote"]:
        result = _promote_user(parts[2:], user_manager)
        if result.message:
            if result.ok:
                logger.info("%s", result.message)
            else:
                logger.warning("%s", result.message)
        return result

    result = ConsoleCommandResult(False, f"Unknown command: {parts[0]}")
    logger.warning("%s", result.message)
    return result


def command_help_text() -> str:
    return "\n".join(
        [
            "Available console commands:",
            "  help",
            "  user promote <username-or-id> [USER|ADMIN|OWNER]",
        ]
    )


def start_console_command_loop(stdin: TextIO | None = None) -> threading.Thread:
    stream = stdin

    def _loop() -> None:
        logger.info("Console command loop started. Type 'help' for commands.")
        while True:
            try:
                line = input("> ") if stream is None else stream.readline()
            except (EOFError, OSError):
                logger.info("Console command loop stopped.")
                return
            if line == "":
                return
            result = execute_console_command(line.strip())
            if result.message and not result.ok:
                logger.error("%s", result.message)

    thread = threading.Thread(target=_loop, name="trpg-console-commands", daemon=True)
    thread.start()
    return thread


def _promote_user(args: list[str], user_manager: Any) -> ConsoleCommandResult:
    if not args:
        return ConsoleCommandResult(False, "Usage: user promote <username-or-id> [USER|ADMIN|OWNER]")

    identifier = args[0]
    role = args[1].upper() if len(args) > 1 else "ADMIN"
    if role not in VALID_ROLES:
        return ConsoleCommandResult(False, f"Invalid role: {role}")

    user = _find_user(identifier, user_manager)
    if not user:
        return ConsoleCommandResult(False, f"User not found: {identifier}")

    success, message = user_manager.update_user_role(int(user["id"]), role)
    if not success:
        return ConsoleCommandResult(False, message)
    return ConsoleCommandResult(True, f"Updated {user.get('username') or user['id']} role to {role}")


def _find_user(identifier: str, user_manager: Any) -> dict[str, Any] | None:
    if identifier.isdigit() and hasattr(user_manager, "get_user_by_id"):
        user = user_manager.get_user_by_id(int(identifier))
        if user:
            return user

    identifier_lower = identifier.lower()
    for user in user_manager.get_all_users():
        if str(user.get("id")) == identifier or str(user.get("username", "")).lower() == identifier_lower:
            return user
    return None
