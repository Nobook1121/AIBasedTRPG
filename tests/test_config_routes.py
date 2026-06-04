import json

from trpg_server.app_factory import create_app


def _config_app(tmp_path):
    config_dir = tmp_path / "config"
    app = create_app()
    app.config["CONFIG_DIR"] = config_dir
    app.config["AI_PLATFORM_DIR"] = config_dir / "aiplatform"
    app.config["AI_MODEL_DIR"] = config_dir / "aimodel"
    return app, config_dir


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


def test_config_route_saves_model_js(tmp_path):
    app, config_dir = _config_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/api/config/aimodel/save",
        json={"platform": "openai", "modelId": "gpt", "content": "export default {};"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert (
        config_dir / "aimodel" / "openai" / "gpt.js"
    ).read_text(encoding="utf-8") == "export default {};"


def test_config_route_deletes_model_js(tmp_path):
    app, config_dir = _config_app(tmp_path)
    model_dir = config_dir / "aimodel" / "openai"
    model_dir.mkdir(parents=True)
    model_file = model_dir / "gpt.js"
    model_file.write_text("export default {};", encoding="utf-8")
    client = app.test_client()

    response = client.post(
        "/api/config/aimodel/delete",
        json={"platform": "openai", "modelId": "gpt"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert not model_file.exists()
