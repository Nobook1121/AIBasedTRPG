class FakeUserManager:
    def __init__(self):
        self.users = [
            {"id": 1, "username": "alice", "role": "USER"},
            {"id": 2, "username": "bob", "role": "USER"},
        ]
        self.updated = []

    def get_all_users(self):
        return self.users

    def update_user_role(self, user_id, role):
        self.updated.append((user_id, role))
        return True, "Role updated successfully"


class FakeSessionUserManager:
    def is_session_current(self, user_id, token):
        return True

    def get_user_by_id(self, user_id):
        return {
            "id": user_id,
            "username": "alice",
            "email": "alice@example.com",
            "role": "ADMIN",
        }


def test_console_command_promotes_user_by_username():
    from trpg_server.console_commands import execute_console_command

    manager = FakeUserManager()

    result = execute_console_command("user promote alice ADMIN", user_manager=manager)

    assert result.ok
    assert manager.updated == [(1, "ADMIN")]
    assert "alice" in result.message


def test_console_command_rejects_unknown_command():
    from trpg_server.console_commands import execute_console_command

    result = execute_console_command("does-not-exist")

    assert not result.ok
    assert "Unknown command" in result.message


def test_auth_status_refreshes_session_role_after_console_promotion():
    from trpg_server.app_factory import create_app

    app = create_app({"TESTING": True, "USER_MANAGER": FakeSessionUserManager()})
    client = app.test_client()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "alice"
        session["role"] = "USER"
        session["session_token"] = "token"

    response = client.get("/api/auth/status")

    assert response.status_code == 200
    with client.session_transaction() as session:
        assert session["role"] == "ADMIN"


def test_console_promote_is_emitted_through_logging(caplog):
    from trpg_server.console_commands import execute_console_command

    manager = FakeUserManager()
    with caplog.at_level("INFO", logger="trpg_server.console_commands"):
        result = execute_console_command("user promote alice ADMIN", user_manager=manager)

    assert result.ok
    assert "alice" in caplog.text
    assert "ADMIN" in caplog.text


def test_compact_formatter_uses_thread_name_in_log_format():
    import logging

    from trpg_server.logging_config import CompactFormatter

    record = logging.LogRecord(
        name="trpg_server.console_commands",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="promoted",
        args=(),
        exc_info=None,
    )
    record.threadName = "trpg-console-commands"

    rendered = CompactFormatter("[%(asctime)s][%(levelname)s][%(threadName)s] %(message)s").format(record)

    assert "[INFO][trpg-console-commands] promoted" in rendered
