from trpg_server.app_factory import create_app


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
