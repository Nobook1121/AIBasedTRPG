from pathlib import Path


def test_frontend_displays_cache_rate_and_token_dashboard():
    chat = Path("frontend/src/app/chat.ts").read_text(encoding="utf-8")
    settings = Path("frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    tabs = Path("frontend/src/app/tabs.ts").read_text(encoding="utf-8")

    assert "缓存命中率" in chat
    assert "cache_hit_rate" in chat
    assert "prefix_cache_hit" in chat
    assert "前缀缓存命中率" in settings
    assert 'id="aiTokenDashboard"' in settings
    assert 'id="aiTokenDashboardBody"' in settings
    assert "/api/telemetry/ai/daily" in tabs
    assert "Object.entries(response.data.roles" in tabs


def test_frontend_moves_usage_to_dedicated_settings_tab_and_adds_room_exit():
    rooms_template = Path("frontend/src/templates/rooms.html").read_text(encoding="utf-8")
    rooms_source = Path("frontend/src/app/rooms.ts").read_text(encoding="utf-8")
    settings = Path("frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    assert 'data-settings="usage"' in settings
    character_section = settings.split('id="character-settings-content"', 1)[1].split('id="permissions-settings-content"', 1)[0]
    assert 'id="aiTokenDashboard"' not in character_section
    assert 'id="aiUsageChart"' in settings
    assert 'id="aiUsageHeatmap"' in settings
    assert 'data-action="leave-room"' in rooms_template
    assert '/leave' in rooms_source
