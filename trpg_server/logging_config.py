import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {"api_key", "auth_token", "token", "password", "secret", "secret_key"}
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
