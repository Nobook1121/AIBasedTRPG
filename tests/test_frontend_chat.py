from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHAT_JS = PROJECT_ROOT / "js" / "chat.js"


def _chat_source():
    return CHAT_JS.read_text(encoding="utf-8")


def test_player_messages_use_current_username_instead_of_me_label():
    source = _chat_source()

    assert "function getCurrentUsername()" in source
    assert "addMessage('player', '我', message)" not in source
    assert "broadcastMessage('player', '我', message)" not in source


def test_processing_metadata_is_rendered_only_for_ai_messages():
    source = _chat_source()

    assert "processingTime !== null && type === 'kp'" in source
    assert "type === 'kp'" in source


def test_room_messages_compare_sender_id_instead_of_session_label():
    source = _chat_source()

    assert "message.sender_id === getCurrentUserId()" in source
    assert "addMessage('other', data.sender ||" not in source


def test_room_messages_use_persisted_sender_avatar():
    source = _chat_source()

    assert "message.avatar" in source
    assert "getAvatarSrc(type, message)" in source


def test_chat_requires_login_and_room_before_sending():
    source = _chat_source()

    assert "window.currentUser" in source
    assert "请先登录后再发送消息" in source
    assert "showAuthModal" in source
    assert "请先加入房间后再发送消息" in source
    assert "if (!getCurrentRoom())" in source


def test_ai_mentions_keep_kp_prefix_for_visible_message_and_ai_request():
    source = _chat_source()

    assert "const message = rawMessage" in source
    assert "findRoleForMessage(rawMessage)" in source
    assert "trimmedMessage.startsWith(wakeWord)" in source
    assert "rawMessage.substring(aiName.length + 1)" not in source
