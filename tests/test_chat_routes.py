import logging

from trpg_server.app_factory import create_app


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def test_home_message_returns_echo_payload():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/messages",
        json={"user_id": "u1", "content": "hello"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "u1"
    assert data["data"]["content"] == "hello"
    assert "timestamp" in data["data"]


def test_home_message_rejects_empty_content():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/messages", json={"user_id": "u1", "content": ""})

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_scenario_message_returns_script_payload():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/scenarios/12/messages",
        json={"user_id": "u1", "content": "look"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["script_id"] == 12
    assert data["data"]["content"] == "look"


def test_chat_rejects_missing_payload():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/chat")

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_chat_rejects_when_no_ai_platform_is_enabled(tmp_path):
    app = create_app()
    app.config["AI_PLATFORM_DIR"] = tmp_path / "aiplatform"
    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={"user_id": "u1", "content": "hello"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "error" in data


def test_chat_logs_ai_request_and_response_content(tmp_path, monkeypatch):
    platform_dir = tmp_path / "aiplatform"
    platform_dir.mkdir()
    (platform_dir / "test.json").write_text(
        """
        {
          "enabled": true,
          "config": {"api_key": "secret", "base_url": "http://ai.local/chat"},
          "models": [{"id": "test-model", "enabled": true}]
        }
        """,
        encoding="utf-8",
    )
    prompt_file = tmp_path / "kp.md"
    prompt_file.write_text("你是KP", encoding="utf-8")

    class Response:
        ok = True
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": "门缓缓打开。"}}],
                "usage": {"total_tokens": 12},
            }

    def fake_post(url, headers, json, timeout):
        return Response()

    monkeypatch.setattr("trpg_server.routes.chat.requests.post", fake_post)
    app = create_app(
        {
            "AI_PLATFORM_DIR": platform_dir,
            "HISTORY_DIR": tmp_path / "history",
            "KP_PROMPT_FILE": prompt_file,
            "USER_DATABASE_FILE": tmp_path / "users.sqlite3",
            "USERS_FILE": tmp_path / "users.json",
        }
    )
    client = app.test_client()

    logger = logging.getLogger("trpg_server.routes.chat")
    handler = ListHandler()
    logger.addHandler(handler)
    try:
        response = client.post("/api/chat", json={"user_id": "u1", "content": "@KP 开门"})
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 200
    assert any("request_content=@KP 开门" in message for message in handler.messages)
    assert any("ai_response=门缓缓打开。" in message for message in handler.messages)
