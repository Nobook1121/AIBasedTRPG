import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {"api_key", "auth_token", "token", "password", "secret", "secret_key"}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if key.lower() in SENSITIVE_KEYS else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def configure_logging(log_dir: str | Path = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / "ai_trpg.log"

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def register_request_logging(app) -> None:
    logger = logging.getLogger("trpg_server.requests")

    @app.before_request
    def _start_request_timer():
        from flask import g

        g.request_started_at = time.perf_counter()

    @app.after_request
    def _log_response(response):
        from flask import g, request, session

        elapsed_ms = int(
            (time.perf_counter() - g.get("request_started_at", time.perf_counter()))
            * 1000
        )
        logger.info(
            "%s %s status=%s elapsed_ms=%s user_id=%s client_ip=%s",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
            session.get("user_id"),
            request.remote_addr,
        )
        return response
