from pathlib import Path


def test_kp_prompt_is_valid_chinese_and_requires_tools_for_dice():
    prompt = Path("data/config/roles/kp.md").read_text(encoding="utf-8")

    assert "浣犳槸" not in prompt
    assert "你是KP" in prompt
    assert "COC7" in prompt
    assert "不得编造骰点" in prompt
    assert "room.get_room_snapshot" in prompt
    assert "dice.roll_coc_check" in prompt
    assert "不无故让调查员死亡" in prompt
    assert "失败归因" in prompt


def test_general_config_contains_ai_stream_output_flag():
    general_config = Path("data/config/general.toml").read_text(encoding="utf-8")

    assert "[ai]" in general_config
    assert "stream_output = false" in general_config


def test_frontend_settings_exposes_ai_stream_output_toggle():
    settings_html = Path("frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    config_source = Path("frontend/src/js/config/ConfigManager.ts").read_text(encoding="utf-8")
    tabs_source = Path("frontend/src/js/tabs.ts").read_text(encoding="utf-8")

    assert 'id="streamOutput"' in settings_html
    assert "stream_output" in config_source
    assert "streamOutput" in tabs_source
