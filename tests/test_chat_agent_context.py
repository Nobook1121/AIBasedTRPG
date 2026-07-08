from pathlib import Path

from flask import Flask, session

from trpg_server.routes.chat import (
    _build_messages,
    _history_filename,
    _post_ai_request,
    _room_snapshot_system_message,
)
from trpg_server.routes.characters import _runtime_to_test_character, _test_character_to_runtime
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


def test_room_snapshot_system_message_omits_large_character_and_scenario_details():
    snapshot = {
        "room": {"id": "room-1", "name": "\u6d4b\u8bd5\u623f\u95f4"},
        "scenario": {
            "id": 7,
            "title": "\u957f\u751f\u4fd1",
            "description": "\u897f\u5b89\u8c03\u67e5",
            "background": "\u4e0d\u5e94\u8be5\u8fdb\u5165\u6bcf\u8f6e AI \u8bf7\u6c42\u7684\u5b8c\u6574\u80cc\u666f",
            "scenes": [{"id": 1, "content": "\u897f\u5b89\u9ad8\u94c1\u7ad9"}],
        },
        "members": [
            {
                "username": "ADMIN",
                "character_card": {
                    "id": "investigator-1",
                    "name": "\u5434\u660e\u5c71",
                    "attributes": {"DEX": 55, "STR": 60},
                    "skills": [{"name": "\u4fa6\u5bdf", "value": 70}],
                    "background": {"story": "\u5931\u8e2a\u8bb0\u8005"},
                },
                "character_state": {"current_san": 50},
            }
        ],
    }

    message = _room_snapshot_system_message(snapshot)

    assert "room.get_room_snapshot" in message
    assert "\u957f\u751f\u4fd1" in message
    assert "\u5434\u660e\u5c71" in message
    assert "skills" not in message
    assert "attributes" not in message
    assert "\u4fa6\u5bdf" not in message
    assert "DEX" not in message
    assert "\u897f\u5b89\u9ad8\u94c1\u7ad9" not in message


def test_room_snapshot_system_message_preserves_compact_snapshot_details():
    snapshot = {
        "room": {"id": "room-1", "name": "test room"},
        "scenario": {
            "id": 7,
            "title": "Long Life Figurine",
            "description": "scenario summary",
            "found": True,
            "available_sections": {"scenes": 3},
        },
        "members": [
            {
                "user_id": 9,
                "username": "ADMIN",
                "active": True,
                "character": {"id": "investigator-1", "name": "Wu Mingshan"},
                "character_state": {"current_san": 50},
            }
        ],
    }

    message = _room_snapshot_system_message(snapshot)

    assert "Wu Mingshan" in message
    assert '"scenes": 3' in message


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


def test_login_success_does_not_report_post_login_initialization_errors_as_login_failure():
    source = Path("frontend/src/js/auth/login-view.ts").read_text(encoding="utf-8")

    assert "async function restorePostLoginState" in source
    assert "await restorePostLoginState();" in source

    restore_block = source.split("async function restorePostLoginState", 1)[1]
    assert 'showMessage("loginMessage"' not in restore_block
    assert "await window.autoLoadLastRoom?.();" in restore_block


def test_character_template_exports_skill_base_key_instead_of_hardcoded_base():
    character = {
        "id": "investigator-1",
        "name": "Alice",
        "skills": [
            {
                "id": "libraryUse",
                "skillKey": "libraryUse",
                "baseKey": "libraryUse",
                "name": "Library Use",
                "base": 20,
                "value": 45,
                "category": "explore",
            }
        ],
    }

    payload = _runtime_to_test_character(character)
    skill = payload["skillGroups"]["explore"][0]

    assert skill["baseKey"] == "libraryUse"
    assert "base" not in skill


def test_character_template_import_preserves_skill_base_key_without_base_value():
    payload = {
        "id": "investigator-1",
        "name": "Alice",
        "skillGroups": {
            "explore": [
                {
                    "id": "libraryUse",
                    "skillKey": "libraryUse",
                    "baseKey": "libraryUse",
                    "name": "Library Use",
                    "job": 20,
                    "interest": 5,
                    "growth": 0,
                    "value": 45,
                }
            ]
        },
    }

    character = _test_character_to_runtime(payload)
    skill = character["skills"][0]

    assert skill["baseKey"] == "libraryUse"
    assert "base" not in skill


def test_frontend_character_template_exports_base_key_not_base_value():
    source = Path("frontend/src/js/character-sheet.ts").read_text(encoding="utf-8")

    export_block = source.split("function convertCardToTestCharacterJson", 1)[1].split(
        "function convertTestCharacterJsonToCardInput",
        1,
    )[0]
    assert "baseKey:" in export_block
    assert "base: skill.base" not in export_block
