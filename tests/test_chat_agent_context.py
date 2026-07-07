import json

from flask import Flask, session

from trpg_server.app_factory import create_app
from trpg_server.agents.runtime import AgentCompletionResult
from trpg_server.routes.chat import (
    _build_messages,
    _build_provider_request,
    _extract_provider_response,
    _history_filename,
    _post_ai_request,
    _provider_headers,
    _resolve_provider_endpoint,
    _room_snapshot_system_message,
)
from trpg_server.socket_events import register_socket_events
from trpg_server.routes.rooms import create_room_message


def _test_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "AI_PLATFORM_DIR": tmp_path / "aiplatform",
            "USER_DATABASE_FILE": tmp_path / "users.sqlite3",
            "USERS_FILE": tmp_path / "users.json",
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
            "LOGS_DIR": tmp_path / "logs",
        }
    )


def _write_platform(directory, name, config):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.json").write_text(json.dumps(config), encoding="utf-8")


def test_history_filename_is_room_scoped_when_room_is_available():
    assert _history_filename("user-1", "room-alpha", "kp") == "room-room-alpha-kp.json"
    assert _history_filename("user-1", "room-beta", "kp") == "room-room-beta-kp.json"


def test_history_filename_falls_back_to_user_for_non_room_chat():
    assert _history_filename("user-1", None, "kp") == "user-user-1-kp.json"


def test_build_messages_includes_room_snapshot_context():
    snapshot = {
        "room": {"id": "room-1", "name": "测试房间"},
        "scenario": {"title": "长生俑", "summary": "剧本《长生俑》。场景：西安高铁站。"},
        "members": [
            {
                "username": "ADMIN",
                "character": {"name": "吴明山", "summary": "调查员吴明山，背景：失踪记者。"},
            }
        ],
    }

    message = _room_snapshot_system_message(snapshot)
    messages = _build_messages("KP prompt", [], "@KP 开始", room_snapshot_message=message)

    assert messages[0] == {"role": "system", "content": "KP prompt"}
    assert messages[1]["role"] == "system"
    assert "room.get_room_snapshot" in messages[1]["content"]
    assert "长生俑" in messages[1]["content"]
    assert "吴明山" in messages[1]["content"]
    assert '"scenario"' not in messages[1]["content"]
    assert '"members"' not in messages[1]["content"]
    assert "character_card" not in messages[1]["content"]
    assert "角色卡上下文" not in messages[1]["content"]
    assert "current_san" not in messages[1]["content"]
    assert messages[-1] == {"role": "user", "content": "@KP 开始"}


def test_post_ai_request_logs_full_request_and_response_payload(monkeypatch, caplog):
    class FakeResponse:
        ok = True
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "完整回复"}}], "usage": {"total_tokens": 3}}

    def fake_post(base_url, headers, json, timeout):
        assert base_url == "https://example.test/chat"
        assert headers["Authorization"] == "Bearer secret"
        assert json["messages"][0]["content"] == "系统提示"
        return FakeResponse()

    monkeypatch.setattr("trpg_server.routes.chat.requests.post", fake_post)
    caplog.set_level("INFO", logger="trpg_server.routes.chat")

    requester = _post_ai_request("https://example.test/chat", {"Authorization": "Bearer secret"})
    response = requester({"model": "model-a", "messages": [{"role": "system", "content": "系统提示"}]})

    assert response["choices"][0]["message"]["content"] == "完整回复"
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "AI API request payload" in log_text
    assert "系统提示" in log_text
    assert "AI API response payload" in log_text
    assert "完整回复" in log_text


def test_room_message_logs_display_name_and_full_content(monkeypatch, caplog):
    room_info = {
        "members": [
            {
                "user_id": 1,
                "username": "alice",
                "avatar": "/avatar.jpg",
                "status": "active",
            }
        ]
    }
    messages = []

    import trpg_server.routes.rooms as rooms_routes

    def write_messages(room_dir, saved):
        messages[:] = saved

    monkeypatch.setattr(rooms_routes, "_find_room", lambda room_id: ("room-dir", room_info))
    monkeypatch.setattr(rooms_routes, "_read_messages", lambda room_dir: messages.copy())
    monkeypatch.setattr(rooms_routes, "_write_messages", write_messages)
    monkeypatch.setattr(rooms_routes, "_write_room", lambda room_dir, info: None)
    caplog.set_level("INFO", logger="trpg_server.routes.rooms")

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context(
        "/api/rooms/room-1/messages",
        method="POST",
        json={"content": "hello from player", "type": "player"},
    ):
        session["user_id"] = 1
        session["username"] = "alice"
        response, status = create_room_message("room-1")

    assert status == 201
    assert response.get_json()["data"]["content"] == "hello from player"
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "alice:hello from player" in log_text
    assert "用户ID" not in log_text
    assert "房间ID" not in log_text
    assert "消息类型" not in log_text
    assert "内容长度" not in log_text


def test_socket_broadcast_does_not_log_persisted_room_message(monkeypatch, caplog):
    class FakeSocketIO:
        def __init__(self):
            self.handlers = {}
            self._trpg_events_registered = False

        def on(self, event_name):
            def decorator(handler):
                self.handlers[event_name] = handler
                return handler

            return decorator

    fake_socket = FakeSocketIO()
    register_socket_events(fake_socket)
    import trpg_server.socket_events as socket_events

    monkeypatch.setattr(socket_events, "emit", lambda *args, **kwargs: None)
    caplog.set_level("INFO", logger="trpg_server.socket_events")

    app = Flask(__name__)
    app.secret_key = "test"
    app.config["ACTIVE_SESSIONS"] = {}
    with app.test_request_context("/socket.io/"):
        session["user_id"] = 1
        session["username"] = "alice"
        fake_socket.handlers["send_message"](
            {
                "room_id": "room-1",
                "message": {
                    "sender_name": "alice",
                    "content": "hello from player",
                    "type": "player",
                },
            }
        )

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "alice:hello from player" not in log_text


def test_resolve_openai_endpoint_preserves_full_chat_completions_url():
    config = {
        "api_format": "openai",
        "config": {"base_url": "https://api.example.test/v1/chat/completions"},
    }

    assert _resolve_provider_endpoint(config) == "https://api.example.test/v1/chat/completions"


def test_resolve_openai_endpoint_appends_chat_completions_to_v1_base():
    config = {
        "api_format": "openai",
        "config": {"base_url": "https://openrouter.ai/api/v1"},
    }

    assert _resolve_provider_endpoint(config) == "https://openrouter.ai/api/v1/chat/completions"


def test_build_anthropic_request_moves_system_prompt_and_maps_token_fields():
    config = {"api_format": "anthropic", "config": {"api_key": "secret"}}
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "messages": [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
        ],
        "max_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "stream": False,
    }

    request = _build_provider_request(config, payload)

    assert request == {
        "model": "claude-3-5-sonnet-latest",
        "system": "System prompt",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "stream": False,
    }


def test_provider_headers_uses_anthropic_api_key_header():
    config = {
        "api_format": "anthropic",
        "config": {"api_key": "secret", "anthropic_version": "2023-06-01"},
    }

    assert _provider_headers(config) == {
        "Content-Type": "application/json",
        "x-api-key": "secret",
        "anthropic-version": "2023-06-01",
    }


def test_extract_provider_response_supports_anthropic_content_blocks():
    config = {"api_format": "anthropic", "config": {}}
    response = {"content": [{"type": "text", "text": "Hello from Claude"}], "usage": {"output_tokens": 7}}

    assert _extract_provider_response(config, response) == ("Hello from Claude", 7)


def test_extract_provider_response_supports_custom_response_path():
    config = {"api_format": "custom", "custom": {"response_path": "data.answer.text"}}
    response = {"data": {"answer": {"text": "Custom response"}}}

    assert _extract_provider_response(config, response) == ("Custom response", None)


def test_build_custom_request_replaces_template_placeholders():
    config = {
        "api_format": "custom",
        "custom": {
            "request_template": {
                "model": "{{model}}",
                "prompt": "{{last_user_message}}",
                "history": "{{messages}}",
            }
        },
    }
    payload = {
        "model": "custom-model",
        "messages": [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Last question"},
        ],
    }

    assert _build_provider_request(config, payload) == {
        "model": "custom-model",
        "prompt": "Last question",
        "history": payload["messages"],
    }


def test_resolve_anythingllm_endpoint_uses_workspace_slug_model():
    config = {"api_format": "anythingllm", "config": {"base_url": "http://localhost:3001/api/v1"}}
    payload = {"model": "my-workspace"}

    assert _resolve_provider_endpoint(config, payload) == "http://localhost:3001/api/v1/workspace/my-workspace/chat"


def test_resolve_anythingllm_endpoint_prefers_configured_workspace_slug():
    config = {
        "api_format": "anythingllm",
        "config": {"base_url": "http://localhost:3001/api/v1", "workspace_slug": "configured-workspace"},
    }
    payload = {"model": "workspace-slug"}

    assert _resolve_provider_endpoint(config, payload) == "http://localhost:3001/api/v1/workspace/configured-workspace/chat"


def test_build_anythingllm_request_uses_workspace_chat_shape():
    config = {
        "api_format": "anythingllm",
        "config": {"anythingllm_mode": "chat", "session_id": "room-1-kp"},
    }
    payload = {
        "messages": [
            {"role": "system", "content": "System"},
            {"role": "assistant", "content": "Previous"},
            {"role": "user", "content": "Next action?"},
        ],
    }

    assert _build_provider_request(config, payload) == {
        "message": "Next action?",
        "mode": "chat",
        "sessionId": "room-1-kp",
        "attachments": [],
        "reset": False,
    }


def test_extract_anythingllm_response_reads_text_response():
    config = {"api_format": "anythingllm", "config": {}}
    response = {"type": "textResponse", "textResponse": "AnythingLLM answer", "sources": []}

    assert _extract_provider_response(config, response) == ("AnythingLLM answer", None)


def test_list_ai_platforms_returns_json_configs_and_skips_default_request(tmp_path):
    platform_dir = tmp_path / "aiplatform"
    _write_platform(
        platform_dir,
        "custom-provider",
        {
            "platform": "custom-provider",
            "name": "Custom Provider",
            "description": "Custom",
            "icon": "/assets/aiplatform/default.png",
            "enabled": True,
            "config": {"base_url": "https://api.example.test/v1", "timeout": 30},
            "models": [],
        },
    )
    (platform_dir / "default-request.json").write_text("{}", encoding="utf-8")
    app = _test_app(tmp_path)

    response = app.test_client().get("/api/config/aiplatforms")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert [item["platform"] for item in body["data"]] == ["custom-provider"]


def test_ai_platform_test_route_uses_anthropic_request_shape(tmp_path, monkeypatch):
    platform_dir = tmp_path / "aiplatform"
    _write_platform(
        platform_dir,
        "anthropic-custom",
        {
            "platform": "anthropic-custom",
            "name": "Anthropic Custom",
            "description": "Anthropic",
            "icon": "/assets/aiplatform/default.png",
            "enabled": True,
            "api_format": "anthropic",
            "config": {
                "api_key": "secret",
                "base_url": "https://api.anthropic.com/v1/messages",
                "timeout": 30,
            },
            "models": [],
        },
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"content": [{"type": "text", "text": "ok"}], "usage": {"output_tokens": 1}}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("trpg_server.routes.config.requests.post", fake_post)
    app = _test_app(tmp_path)

    response = app.test_client().post(
        "/api/config/aiplatform/anthropic-custom/test",
        json={
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "Hello"},
            ],
            "max_tokens": 256,
        },
    )

    assert response.status_code == 200
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "secret"
    assert "Authorization" not in captured["headers"]
    assert captured["json"]["system"] == "System"
    assert captured["json"]["messages"] == [{"role": "user", "content": "Hello"}]


def test_ai_platform_test_route_handles_string_error_response(tmp_path, monkeypatch):
    platform_dir = tmp_path / "aiplatform"
    _write_platform(
        platform_dir,
        "anythingllm",
        {
            "platform": "anythingllm",
            "name": "AnythingLLM",
            "description": "AnythingLLM",
            "icon": "/assets/aiplatform/anythingllm.png",
            "enabled": True,
            "api_format": "anythingllm",
            "config": {
                "api_key": "bad-key",
                "base_url": "http://localhost:3001/api/v1",
                "timeout": 30,
                "anythingllm_mode": "chat",
            },
            "models": [{"id": "workspace-slug", "name": "Workspace", "description": "", "enabled": True}],
        },
    )

    class FakeResponse:
        status_code = 403

        def json(self):
            return "Invalid API Key"

    monkeypatch.setattr("trpg_server.routes.config.requests.post", lambda *args, **kwargs: FakeResponse())
    app = _test_app(tmp_path)

    response = app.test_client().post(
        "/api/config/aiplatform/anythingllm/test",
        json={"model": "workspace-slug", "messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Invalid API Key"


def test_chat_route_uses_provider_aware_requester(tmp_path, monkeypatch):
    platform_dir = tmp_path / "aiplatform"
    _write_platform(
        platform_dir,
        "custom-provider",
        {
            "platform": "custom-provider",
            "name": "Custom Provider",
            "description": "Custom",
            "icon": "/assets/aiplatform/default.png",
            "enabled": True,
            "api_format": "custom",
            "config": {
                "api_key": "secret",
                "base_url": "https://api.example.test/chat",
                "timeout": 30,
            },
            "custom": {"response_path": "answer"},
            "models": [{"id": "custom-model", "name": "Custom", "description": "", "enabled": True}],
        },
    )
    sentinel_requester = object()
    seen = {}

    def fake_post_provider_request(platform_config):
        seen["platform_config"] = platform_config
        return sentinel_requester

    def fake_run_agent_completion(requester, base_payload, profile, registry, context):
        seen["requester"] = requester
        seen["base_payload"] = base_payload
        return AgentCompletionResult(content="Provider aware response", token_count=3)

    monkeypatch.setattr(
        "trpg_server.routes.chat._load_role_for_content",
        lambda content: {"id": "npc", "name": "NPC", "provider": "custom-provider", "prompt": "Prompt"},
    )
    monkeypatch.setattr("trpg_server.routes.chat._post_provider_request", fake_post_provider_request)
    monkeypatch.setattr("trpg_server.routes.chat.run_agent_completion", fake_run_agent_completion)
    app = _test_app(tmp_path)

    response = app.test_client().post("/api/chat", json={"user_id": "u1", "content": "Hello"})

    assert response.status_code == 200
    assert response.get_json()["content"] == "Provider aware response"
    assert seen["platform_config"]["api_format"] == "custom"
    assert seen["requester"] is sentinel_requester
    assert seen["base_payload"]["model"] == "custom-model"
