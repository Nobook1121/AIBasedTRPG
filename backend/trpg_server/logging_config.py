import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {"api_key", "auth_token", "token", "password", "secret", "secret_key"}
MAX_LOG_VALUE_LENGTH = 200
LEVEL_LABELS = {
    logging.WARNING: "WARN",
    logging.CRITICAL: "FATAL",
}


class CompactFormatter(logging.Formatter):
    def format(self, record):
        original_levelname = record.levelname
        record.levelname = LEVEL_LABELS.get(record.levelno, record.levelname)
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if key.lower() in SENSITIVE_KEYS else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def user_action_text(username: Any = None, action: str = "进行了操作") -> str:
    display_name = str(username or "未知用户").strip() or "未知用户"
    return f"用户 {display_name} {action}"


def log_user_action(logger: logging.Logger, message: str, **details: Any) -> None:
    safe_details = redact_sensitive(details)
    detail_text = _format_details(safe_details)
    if detail_text:
        logger.info("%s；%s", message, detail_text)
        return
    logger.info("%s", message)


def _format_details(details: dict[str, Any]) -> str:
    parts = []
    for key, value in details.items():
        if value is None or value == "":
            continue
        parts.append(f"{key}={_format_log_value(value)}")
    return "，".join(parts)


def _format_log_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    if len(text) > MAX_LOG_VALUE_LENGTH:
        return f"{text[:MAX_LOG_VALUE_LENGTH]}..."
    return text


def configure_logging(log_dir: str | Path = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(log_dir) / f"ai_trpg_{started_at}.log"

    formatter = CompactFormatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s")

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

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
