from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTH_LOGIN_JS = PROJECT_ROOT / "js" / "auth" / "login-view.js"
AUTH_USER_CARD_JS = PROJECT_ROOT / "js" / "auth" / "user-card.js"
ROOMS_JS = PROJECT_ROOT / "js" / "rooms.js"
MAIN_JS = PROJECT_ROOT / "js" / "main.js"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_auth_initialization_is_awaited_before_room_autoload():
    source = _read(MAIN_JS)

    assert "await initAuth()" in source
    assert source.index("await initAuth()") < source.index("initRoomManagement()")
    assert source.index("initRoomManagement()") < source.index("await autoLoadLastRoom()")


def test_login_reconnects_socket_and_reloads_user_scoped_room():
    source = _read(AUTH_LOGIN_JS)

    assert "window.reconnectSocket?.()" in source
    assert "window.autoLoadLastRoom?.()" in source


def test_logout_clears_room_and_chat_before_account_switch():
    source = _read(AUTH_USER_CARD_JS)

    assert "window.clearCurrentRoom?.()" in source
    assert "window.clearChatMessages?.()" in source


def test_last_room_cache_is_scoped_by_user_id():
    source = _read(ROOMS_JS)

    assert "trpg_last_room_${window.currentUser?.user_id}" in source
    assert "TrpgCookies.set(getLastRoomStorageKey()" in source
    assert "TrpgCookies.get(getLastRoomStorageKey())" in source


def test_room_scenario_select_uses_unique_id_and_status_ui_is_rich():
    index_source = _read(PROJECT_ROOT / "index.html")
    rooms_source = _read(ROOMS_JS)

    assert 'id="roomScenarioSelect"' in index_source
    assert 'id="saveScenario"' not in index_source.split('id="createSaveModal"')[1].split('id="settings"')[0]
    assert "roomScenarioSelect" in rooms_source
    assert "save-status-pill" in index_source
    assert "save-status-script" in index_source
