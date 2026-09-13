import json

from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.role_config import provider_small_model_config


def test_runtime_config_reads_small_model_task_mapping(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "general.toml").write_text(
        "[ai.small_models]\nintent_classification = \"qwen-turbo\"\n",
        encoding="utf-8",
    )

    config = load_ai_runtime_config(config_dir)

    assert config.small_model_tasks["intent_classification"] == "qwen-turbo"
    assert "summarization" in config.small_model_tasks


def test_provider_small_model_config_prefers_task_model_and_falls_back():
    provider = {
        "models": [{"id": "primary", "enabled": True}],
        "small_models": {
            "summarization": {"id": "small-summary", "enabled": True},
        },
    }

    assert provider_small_model_config(provider, "summarization")["id"] == "small-summary"
    assert provider_small_model_config(provider, "state_update")["id"] == "primary"


def test_openai_provider_template_is_openai_compatible():
    config = json.loads(open("data/config/aiplatform/openai.json", encoding="utf-8").read())
    assert config["enabled"] is False
    assert config["config"]["base_url"].endswith("/chat/completions")
    assert config["small_models"]["summarization"]["id"] == "gpt-4o-mini"
