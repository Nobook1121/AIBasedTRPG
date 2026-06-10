import json
import tomllib

from trpg_server.app_factory import create_app
from trpg_server.routes.config import convert_to_toml


def _config_app(tmp_path):
    config_dir = tmp_path / "config"
    app = create_app()
    app.config["CONFIG_DIR"] = config_dir
    app.config["AI_PLATFORM_DIR"] = config_dir / "aiplatform"
    app.config["AI_MODEL_DIR"] = config_dir / "aimodel"
    app.config["KP_PROMPT_FILE"] = config_dir / "roles" / "kp.md"
    app.config["ROLE_CONFIG_FILE"] = config_dir / "roles" / "roles.json"
    return app, config_dir


class _PromptUserManager:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def is_session_current(self, user_id, token):
        return True

    def check_permission(self, user_id, required_role):
        return self.allowed and required_role == "ADMIN"


def _login_as_admin(client, app, allowed=True):
    app.config["USER_MANAGER"] = _PromptUserManager(allowed=allowed)
    with client.session_transaction() as flask_session:
        flask_session["user_id"] = "admin"
        flask_session["session_token"] = "token"


def test_config_route_saves_toml_file(tmp_path):
    app, config_dir = _config_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/api/config/game",
        json={"general": {"name": "TRPG", "enabled": True, "limit": 3}},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert (config_dir / "game.toml").read_text(encoding="utf-8") == (
        "[general]\n"
        "enabled = true\n"
        "limit = 3\n"
        'name = "TRPG"\n'
    )


def test_convert_to_toml_escapes_string_values():
    toml_text = convert_to_toml(
        {"general": {"name": 'TRPG "Keeper"\nsecond line'}}
    )

    parsed = tomllib.loads(toml_text)

    assert parsed["general"]["name"] == 'TRPG "Keeper"\nsecond line'


def test_convert_to_toml_quotes_unsafe_section_and_key_names():
    toml_text = convert_to_toml(
        {'general"]\n[injected': {'name"\nother': "TRPG"}}
    )

    parsed = tomllib.loads(toml_text)

    assert parsed['general"]\n[injected']['name"\nother'] == "TRPG"


def test_config_route_saves_ai_platform_json(tmp_path):
    app, config_dir = _config_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/api/config/aiplatform/openai",
        json={"enabled": True, "config": {"base_url": "http://localhost"}},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    data = json.loads((config_dir / "aiplatform" / "openai.json").read_text(encoding="utf-8"))
    assert data["enabled"] is True


def test_config_route_test_ai_platform_returns_404_for_missing_config(tmp_path):
    app, _ = _config_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/api/config/aiplatform/openai/test",
        json={"messages": []},
    )

    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_config_route_saves_model_request_json(tmp_path):
    app, config_dir = _config_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/api/config/aimodel/save",
        json={
            "platform": "openai",
            "modelId": "gpt",
            "content": {
                "messages": [{"role": "user", "content": "a"}],
                "stream": True,
                "temperature": 0.7,
            },
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    data = json.loads(
        (config_dir / "aimodel" / "openai" / "gpt.json").read_text(encoding="utf-8")
    )
    assert data["stream"] is True
    assert data["messages"][0]["content"] == "a"
    assert not (config_dir / "aimodel" / "openai" / "gpt.js").exists()


def test_config_route_deletes_model_request_json(tmp_path):
    app, config_dir = _config_app(tmp_path)
    model_dir = config_dir / "aimodel" / "openai"
    model_dir.mkdir(parents=True)
    model_file = model_dir / "gpt.json"
    model_file.write_text('{"stream": true}', encoding="utf-8")
    client = app.test_client()

    response = client.post(
        "/api/config/aimodel/delete",
        json={"platform": "openai", "modelId": "gpt"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert not model_file.exists()


def test_role_config_requires_admin(tmp_path):
    app, _ = _config_app(tmp_path)
    client = app.test_client()

    response = client.get("/api/config/roles")

    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_role_config_can_be_loaded_and_saved_by_admin(tmp_path):
    app, config_dir = _config_app(tmp_path)
    platform_dir = config_dir / "aiplatform"
    platform_dir.mkdir(parents=True)
    (platform_dir / "lmstudio.json").write_text(
        json.dumps({"enabled": True, "name": "LMStudio", "models": []}),
        encoding="utf-8",
    )
    prompt_file = config_dir / "roles" / "kp.md"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("你是严格但公平的KP", encoding="utf-8")
    client = app.test_client()
    _login_as_admin(client, app)

    get_response = client.get("/api/config/roles")

    assert get_response.status_code == 200
    payload = get_response.get_json()["data"]
    assert payload["roles"][0]["id"] == "kp"
    assert payload["roles"][0]["wake_words"] == ["@KP"]
    assert payload["roles"][0]["prompt"] == "你是严格但公平的KP"
    assert payload["enabled_providers"][0]["id"] == "lmstudio"

    save_response = client.post(
        "/api/config/roles/kp",
        json={
            "wake_words": ["@KP", "@Keeper"],
            "prompt": "你是注重氛围的KP",
            "provider": "lmstudio",
        },
    )

    assert save_response.status_code == 200
    assert save_response.get_json()["success"] is True
    saved = json.loads((config_dir / "roles" / "roles.json").read_text(encoding="utf-8"))
    assert saved["roles"][0]["wake_words"] == ["@KP", "@Keeper"]
    assert saved["roles"][0]["provider"] == "lmstudio"


def test_role_config_rejects_disabled_provider(tmp_path):
    app, config_dir = _config_app(tmp_path)
    platform_dir = config_dir / "aiplatform"
    platform_dir.mkdir(parents=True)
    (platform_dir / "disabled.json").write_text(
        json.dumps({"enabled": False, "name": "Disabled", "models": []}),
        encoding="utf-8",
    )
    client = app.test_client()
    _login_as_admin(client, app)

    response = client.post(
        "/api/config/roles/kp",
        json={"wake_words": ["@KP"], "prompt": "Prompt", "provider": "disabled"},
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
