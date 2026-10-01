from __future__ import annotations

from dataclasses import dataclass
import logging
import shlex
import threading
from typing import Any, Callable, TextIO

from trpg_server.users.manager import user_manager as default_user_manager

logger = logging.getLogger(__name__)

VALID_ROLES = {"USER", "ADMIN", "OWNER"}
# 降级命令只允许落到 USER/ADMIN；OWNER 属于最高权限，不作降级目标。
DEMOTE_TARGETS = {"USER", "ADMIN"}

# The console loop runs in its own thread, separate from the web server.  A
# callback lets the embedding server decide how to perform the actual graceful
# stop (a stoppable WSGI server must be shut down from a different thread than
# the one running its request loop).
_shutdown_callback: Callable[[], None] | None = None
_shutdown_lock = threading.Lock()

# ``shutdown`` is the canonical spelling; the short aliases are convenient when
# typing directly into a local console and all follow the same graceful path.
SHUTDOWN_COMMANDS = {"shutdown", "stop", "quit", "exit", "server shutdown"}


@dataclass
class ConsoleCommandResult:
    ok: bool
    message: str


def set_shutdown_callback(callback: Callable[[], None] | None) -> None:
    """Register the action invoked by the ``shutdown`` console command.

    Passing ``None`` removes a previous callback.  This keeps command parsing
    independent from the concrete web-server runtime and makes the command
    straightforward to exercise in tests.
    """

    global _shutdown_callback
    with _shutdown_lock:
        _shutdown_callback = callback


def _log_result(result: ConsoleCommandResult) -> ConsoleCommandResult:
    """Log a command result exactly once at the level matching its outcome."""

    if result.message:
        if result.ok:
            logger.info("%s", result.message)
        else:
            logger.warning("%s", result.message)
    return result


def _invoke_shutdown_callback(callback_override: Callable[[], None] | None = None) -> ConsoleCommandResult:
    with _shutdown_lock:
        callback = callback_override if callback_override is not None else _shutdown_callback
    if callback is None:
        return ConsoleCommandResult(False, "Shutdown is not available in this server process")
    try:
        callback()
    except Exception as exc:  # pragma: no cover - defensive logging path
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
        return _log_result(ConsoleCommandResult(False, f"Invalid command syntax: {exc}"))

    if not parts:
        return ConsoleCommandResult(True, "")

    if parts[0] in {"help", "?"}:
        return _log_result(ConsoleCommandResult(True, command_help_text()))

    normalized_parts = [part.lower() for part in parts]
    is_shutdown = (
        normalized_parts[0] in {"shutdown", "stop", "quit", "exit"} and len(parts) == 1
    ) or (normalized_parts[:2] == ["server", "shutdown"] and len(parts) == 2)
    if is_shutdown:
        return _log_result(_invoke_shutdown_callback(shutdown_callback))

    # user 子命令统一走 _change_user_role，同时支持升级与降级。
    if parts[0] == "user" and len(parts) >= 2:
        subcommand = parts[1].lower()
        if subcommand == "promote":
            return _log_result(
                _change_user_role(parts[2:], user_manager, "ADMIN", "user promote")
            )
        if subcommand == "demote":
            return _log_result(
                _change_user_role(
                    parts[2:],
                    user_manager,
                    "USER",
                    "user demote",
                    allowed_roles=DEMOTE_TARGETS,
                )
            )

    return _log_result(ConsoleCommandResult(False, f"Unknown command: {parts[0]}"))


def command_help_text() -> str:
    return "\n".join(
        [
            "Available console commands:",
            "  help",
            "  user promote <username-or-id> [USER|ADMIN|OWNER]   （升级，缺省为 ADMIN）",
            "  user demote <username-or-id> [USER|ADMIN]          （降级，缺省为 USER）",
            "  shutdown (aliases: stop, quit, exit, server shutdown)",
        ]
    )


def start_console_command_loop(
    stdin: TextIO | None = None,
    shutdown_callback: Callable[[], None] | None = None,
    user_manager: Any | None = None,
) -> threading.Thread:
    stream = stdin
    # 复用调用方传入的 user_manager（通常与正在运行的 Web 应用是同一实例），
    # 否则退回到模块级默认实例。这样控制台写入与 Web 应用读写的是同一份数据，
    # 避免出现“控制台改了用户组却没有生效”的问题。
    manager = user_manager if user_manager is not None else default_user_manager

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
            command = line.strip()
            # The command itself logs its outcome; the loop must not log it a
            # second time (that produced a duplicate warning + error pair).
            result = execute_console_command(
                command, user_manager=manager, shutdown_callback=shutdown_callback
            )
            # Once a graceful shutdown has been accepted there is no reason to
            # keep the command reader alive.
            if result.ok and command.lower() in SHUTDOWN_COMMANDS:
                logger.info("Console command loop stopped after shutdown request.")
                return

    thread = threading.Thread(target=_loop, name="trpg-console-commands", daemon=True)
    thread.start()
    return thread


def _change_user_role(
    args: list[str],
    user_manager: Any,
    default_role: str,
    command_name: str,
    allowed_roles: set[str] | None = None,
) -> ConsoleCommandResult:
    """调整用户角色/用户组，升级与降级走同一实现。

    ``default_role`` 决定省略目标角色时的默认值（promote 为 ADMIN、demote 为 USER）；
    ``allowed_roles`` 限制可选目标角色，便于让 demote 只能降不能升。
    """

    allowed = allowed_roles or VALID_ROLES
    usage = f"Usage: {command_name} <username-or-id> [{'|'.join(sorted(allowed))}]"
    if not args:
        return ConsoleCommandResult(False, usage)

    identifier = args[0]
    role = args[1].upper() if len(args) > 1 else default_role
    if role not in allowed:
        return ConsoleCommandResult(False, f"Invalid role: {role}. Allowed: {', '.join(sorted(allowed))}")

    user = _find_user(identifier, user_manager)
    if not user:
        return ConsoleCommandResult(False, f"User not found: {identifier}")

    current_role = str(user.get("role") or "USER").upper()
    success, message = user_manager.update_user_role(int(user["id"]), role)
    if not success:
        return ConsoleCommandResult(False, message)
    name = user.get("username") or user["id"]
    if role == current_role:
        return ConsoleCommandResult(True, f"{name} already has role {role}")
    return ConsoleCommandResult(True, f"Updated {name} role {current_role} -> {role}")


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
