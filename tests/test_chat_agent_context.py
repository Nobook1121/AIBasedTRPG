from flask import Flask, session

from trpg_server.routes.chat import (
    _build_messages,
    _history_filename,
    _post_ai_request,
    _room_snapshot_system_message,
)
from trpg_server.socket_events import register_socket_events
from trpg_server.routes.rooms import create_room_message


def test_history_filename_is_room_scoped_when_room_is_available():
    assert _history_filename("user-1", "room-alpha", "kp") == "room-room-alpha-kp.json"
    assert _history_filename("user-1", "room-beta", "kp") == "room-room-beta-kp.json"


def test_history_filename_falls_back_to_user_for_non_room_chat():
    assert _history_filename("user-1", None, "kp") == "user-user-1-kp.json"


def test_build_messages_includes_room_snapshot_context():
    snapshot = {
        "room": {"id": "room-1", "name": "测试房间"},
        "scenario": {"id": 7, "title": "长生俑", "scenes": [{"id": 1, "content": "西安高铁站"}]},
        "members": [
            {
                "username": "ADMIN",
                "character_card": {"name": "吴明山", "background": {"story": "失踪记者"}},
                "character_state": {"current_san": 50},
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
