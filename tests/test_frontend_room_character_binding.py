from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "index.html"
STYLE_CSS = PROJECT_ROOT / "style.css"
ROOMS_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "rooms.ts"
TOOL_MANAGER_TS = PROJECT_ROOT / "frontend" / "src" / "tools" / "toolManager.ts"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_room_ui_has_character_binding_and_record_panels():
    html = _read(INDEX_HTML)

    assert 'id="roomCharacterSelect"' in html
    assert 'id="joinRoomCharacterSelect"' in html
    assert 'id="roomCharacterBindings"' in html
    assert 'id="recordRoomName"' in html
    assert 'id="recordRoomId"' not in html
    assert 'id="recordUsername"' in html
    assert 'id="recordType"' in html
    assert 'id="submitCharacterRecord"' in html
    assert 'data-tool="dice"' in html
    assert 'data-tool="character-record"' in html
    assert 'id="character-record-tool-content"' in html


def test_rooms_frontend_sends_character_card_snapshots_and_renders_records():
    source = _read(ROOMS_TS)

    assert "getSelectedCharacterCardSnapshot" in source
    assert "character_card" in source
    assert "renderRoomCharacterBindings" in source
    assert "character_state" in source
    assert "submitCharacterRecord" in source
    assert "deleteCharacterRecord" in source
    assert "recordRoomName" in source
    assert "/api/rooms/by-name/" in source


def test_room_controls_use_compact_layout_classes():
    html = _read(INDEX_HTML)
    css = _read(STYLE_CSS)

    assert "room-join-toolbar" in html
    assert ".room-join-toolbar" in css
    assert "min-height: 36px" in css


def test_tool_manager_exposes_room_record_helper():
    source = _read(TOOL_MANAGER_TS)

    assert "recordCharacterChange" in source
    assert "window.recordCharacterChange" in source
