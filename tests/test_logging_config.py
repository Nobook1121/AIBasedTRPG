import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from trpg_server.app_factory import create_app
from trpg_server.logging_config import configure_logging, redact_sensitive


def test_redact_sensitive_masks_known_secret_keys():
    payload = {
        "api_key": "secret",
        "auth_token": "token",
        "password": "pass",
        "name": "public",
    }

    assert redact_sensitive(payload) == {
        "api_key": "***",
        "auth_token": "***",
        "password": "***",
        "name": "public",
    }


def test_logging_prefix_uses_requested_level_names(tmp_path):
    configure_logging(tmp_path)

    formatter = logging.getLogger().handlers[0].formatter
    warning_record = logging.LogRecord(
        "trpg_server.test",
        logging.WARNING,
        __file__,
        1,
        "warning message",
        (),
        None,
    )
    fatal_record = logging.LogRecord(
        "trpg_server.test",
        logging.CRITICAL,
        __file__,
        1,
        "fatal message",
        (),
        None,
    )

    assert re.match(r"^\[[^\]]+\]\[WARN\]\[trpg_server\.test\] warning message$", formatter.format(warning_record))
    assert re.match(r"^\[[^\]]+\]\[FATAL\]\[trpg_server\.test\] fatal message$", formatter.format(fatal_record))


def test_log_file_name_includes_creation_timestamp(tmp_path):
    configure_logging(tmp_path)

    file_handler = next(
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, RotatingFileHandler)
    )

    assert re.match(
        r"^ai_trpg_\d{8}_\d{6}\.log$",
        Path(file_handler.baseFilename).name,
    )


def test_werkzeug_access_logs_are_not_emitted_at_info(tmp_path):
    configure_logging(tmp_path)

    assert logging.getLogger("werkzeug").getEffectiveLevel() >= logging.WARNING


def test_generic_get_request_is_not_logged(caplog):
    app = create_app()
    client = app.test_client()

    with caplog.at_level(logging.INFO):
        client.get("/api/scenarios")

    assert not any(
        record.name == "trpg_server.requests" and "GET /api/scenarios" in record.message
        for record in caplog.records
    )
