from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.agents.profiles import DEFAULT_KP_TOOLS, resolve_agent_profile


def test_kp_profile_gets_default_tools_when_role_has_none(tmp_path):
    prompt_file = tmp_path / "kp.md"
    prompt_file.write_text("你是KP。", encoding="utf-8")
    role = {
        "id": "kp",
        "name": "KP",
        "prompt": "你是KP。",
        "provider": "openrouter",
        "wake_words": ["@KP"],
    }

    profile = resolve_agent_profile(role, prompt_file=prompt_file)

    assert profile.id == "kp"
    assert profile.name == "KP"
    assert profile.provider == "openrouter"
    assert profile.prompt == "你是KP。"
    assert profile.tool_names == DEFAULT_KP_TOOLS
    assert profile.wake_words == ["@KP"]


def test_non_kp_profile_defaults_to_no_tools(tmp_path):
    prompt_file = tmp_path / "kp.md"
    prompt_file.write_text("你是KP。", encoding="utf-8")
    profile = resolve_agent_profile(
        {
            "id": "narrator",
            "name": "Narrator",
            "prompt": "旁白。",
            "provider": "lmstudio",
        },
        prompt_file=prompt_file,
    )

    assert profile.id == "narrator"
    assert profile.tool_names == []


def test_role_can_explicitly_select_tools(tmp_path):
    prompt_file = tmp_path / "kp.md"
    prompt_file.write_text("你是KP。", encoding="utf-8")
    profile = resolve_agent_profile(
        {
            "id": "rules",
            "name": "Rules Helper",
            "prompt": "规则助手。",
            "tools": ["dice.roll_coc_check"],
            "context": ["room.recent_messages"],
        },
        prompt_file=prompt_file,
    )

    assert profile.tool_names == ["dice.roll_coc_check"]
    assert profile.context_providers == ["room.recent_messages"]


def test_ai_runtime_config_reads_stream_flag(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "general.toml").write_text("[ai]\nstream_output = true\n", encoding="utf-8")

    config = load_ai_runtime_config(config_dir)

    assert config.stream_output is True
