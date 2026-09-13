from __future__ import annotations

from dataclasses import dataclass
import logging
import shlex
import threading
from typing import Any, Callable, TextIO

from trpg_server.users.manager import user_manager as default_user_manager

logger = logging.getLogger(__name__)

VALID_ROLES = {"USER", "ADMIN", "OWNER"}

# The console loop runs independently from the web server thread.  A callback
# lets the embedding server decide how to perform the actual graceful stop
# (Flask-SocketIO requires its stop method to run inside an HTTP handler).
_shutdown_callback: Callable[[], None] | None = None
_shutdown_lock = threading.Lock()


@dataclass
class ConsoleCommandResult:
    ok: bool
    message: str


def set_shutdown_callback(callback: Callable[[], None] | None) -> None:
    """Register the action invoked by the ``shutdown`` console command.

    Passing ``None`` removes a previous callback.  This small registration API
    keeps command parsing independent from the concrete web-server runtime and
    also makes the command straightforward to exercise in tests.
    """

    global _shutdown_callback
    with _shutdown_lock:
        _shutdown_callback = callback


def _invoke_shutdown_callback(callback_override: Callable[[], None] | None = None) -> ConsoleCommandResult:
    with _shutdown_lock:
        callback = callback_override if callback_override is not None else _shutdown_callback
    if callback is None:
        return ConsoleCommandResult(False, "Shutdown is not available in this server process")
    try:
        callback()
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.exception("Shutdown request failed")
        return ConsoleCommandResult(False, f"Shutdown request failed: {exc}")
    return ConsoleCommandResult(True, "Shutdown requested; waiting for the server to stop safely.")


def execute_console_command(
    command_line: str,
    user_manager: Any = default_user_manager,
    shutdown_callback: Callable[[], None] | None = None,
) -> ConsoleCommandResult:
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

    # ``shutdown`` is the canonical spelling.  The short aliases are useful
    # when operating a local console and all follow the same graceful path.
    normalized_parts = [part.lower() for part in parts]
    if normalized_parts[0] in {"shutdown", "stop", "quit", "exit"} and len(parts) == 1:
        result = _invoke_shutdown_callback(shutdown_callback)
        if result.ok:
            logger.info("%s", result.message)
        else:
            logger.warning("%s", result.message)
        return result

    if normalized_parts[:2] == ["server", "shutdown"] and len(parts) == 2:
        result = _invoke_shutdown_callback(shutdown_callback)
        if result.ok:
            logger.info("%s", result.message)
        else:
            logger.warning("%s", result.message)
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
            "  shutdown (aliases: stop, quit, exit)",
        ]
    )


def start_console_command_loop(
    stdin: TextIO | None = None,
    shutdown_callback: Callable[[], None] | None = None,
) -> threading.Thread:
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
            result = execute_console_command(line.strip(), shutdown_callback=shutdown_callback)
            if result.message and not result.ok:
                logger.error("%s", result.message)
            # Once a graceful shutdown has been accepted there is no reason
            # to keep the command reader alive (and this also lets stdin close
            # cleanly when the process is launched from a script).
            normalized = line.strip().lower()
            if result.ok and (normalized in {"shutdown", "stop", "quit", "exit", "server shutdown"}):
                logger.info("Console command loop stopped after shutdown request.")
                return

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
