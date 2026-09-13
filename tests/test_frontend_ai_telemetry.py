from pathlib import Path


def test_frontend_displays_cache_rate_and_token_dashboard():
    chat = Path("frontend/src/app/chat.ts").read_text(encoding="utf-8")
    settings = Path("frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    tabs = Path("frontend/src/app/tabs.ts").read_text(encoding="utf-8")

    assert "缓存命中率" in chat
    assert "cache_hit_rate" in chat
    assert 'id="aiTokenDashboard"' in settings
    assert 'id="aiTokenDashboardBody"' in settings
    assert "/api/telemetry/ai/daily" in tabs
    assert "Object.entries(response.data.roles" in tabs

