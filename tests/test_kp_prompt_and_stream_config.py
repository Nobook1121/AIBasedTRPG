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
    assert "不要在回复结尾主动提供选项" in prompt
    assert "所有参与玩家的角色卡已经创建完毕" in prompt
    assert "玩家的名字就是其用户名" in prompt
    assert "当前房间绑定的剧本" in prompt


def test_general_config_contains_ai_stream_output_flag():
    general_config = Path("data/config/general.toml").read_text(encoding="utf-8")

    assert "[ai]" in general_config
    assert "stream_output = false" in general_config


def test_frontend_settings_exposes_ai_stream_output_toggle():
    settings_html = Path("frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    config_source = Path("frontend/src/app/config/ConfigManager.ts").read_text(encoding="utf-8")
    tabs_source = Path("frontend/src/app/tabs.ts").read_text(encoding="utf-8")

    assert 'id="streamOutput"' in settings_html
    assert "stream_output" in config_source
    assert "streamOutput" in tabs_source
