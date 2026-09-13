from __future__ import annotations

import json
from pathlib import Path

from trpg_server.app_factory import create_app


class FakeAdminUserManager:
    def is_session_current(self, user_id, token):
        return True

    def get_user_by_id(self, user_id):
        return {
            "id": user_id,
            "username": "admin",
            "role": "ADMIN",
        }


def _write_platform_config(path: Path, api_key: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "platform": "deepseek",
        "name": "DeepSeek",
        "description": "AI service",
        "icon": "/assets/aiplatform/deepseek.png",
        "enabled": True,
        "config": {
            "api_key": api_key,
            "base_url": "https://api.deepseek.com/v1/chat/completions",
            "timeout": 30,
        },
        "models": [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "description": "Chat model",
                "enabled": True,
            },
        ],
    }
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_app(tmp_path: Path):
    config_dir = tmp_path / "config"
    platform_dir = config_dir / "aiplatform"
    secret_dir = tmp_path / "runtime" / "config" / "aiplatform"
    _write_platform_config(platform_dir / "deepseek.json", api_key="public-secret")

    return create_app(
        {
            "TESTING": True,
            "USER_MANAGER": FakeAdminUserManager(),
            "CONFIG_DIR": config_dir,
            "AI_PLATFORM_DIR": platform_dir,
            "AI_PLATFORM_SECRET_DIR": secret_dir,
        }
    )


def test_public_platform_config_strips_api_key_and_migrates_secret(tmp_path: Path):
    app = _build_app(tmp_path)
    client = app.test_client()

    response = client.get("/config/aiplatform/deepseek.json")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["config"]["base_url"] == "https://api.deepseek.com/v1/chat/completions"
    assert "api_key" not in payload["config"]
    assert (tmp_path / "runtime" / "config" / "aiplatform" / "deepseek.json").exists()
    public_text = (tmp_path / "config" / "aiplatform" / "deepseek.json").read_text(encoding="utf-8")
    assert '"api_key"' not in public_text


def test_saving_platform_config_persists_api_key_in_secret_store(tmp_path: Path):
    app = _build_app(tmp_path)
    client = app.test_client()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "ADMIN"
        session["session_token"] = "token"
        session["csrf_token"] = "csrf"

    response = client.post(
        "/api/config/aiplatform/deepseek",
        json={
            "platform": "deepseek",
            "name": "DeepSeek",
            "description": "AI service",
            "icon": "/assets/aiplatform/deepseek.png",
            "enabled": True,
            "config": {
                "api_key": "saved-secret",
                "base_url": "https://api.deepseek.com/v1/chat/completions",
                "timeout": 45,
            },
            "models": [
                {
                    "id": "deepseek-chat",
                    "name": "DeepSeek Chat",
                    "description": "Chat model",
                    "enabled": True,
                },
            ],
        },
        headers={"X-CSRF-Token": "csrf"},
    )

    assert response.status_code == 200
    public_text = (tmp_path / "config" / "aiplatform" / "deepseek.json").read_text(encoding="utf-8")
    secret_text = (tmp_path / "runtime" / "config" / "aiplatform" / "deepseek.json").read_text(encoding="utf-8")
    assert '"api_key"' not in public_text
    assert "saved-secret" in secret_text


def test_saving_platform_config_without_api_key_keeps_existing_secret(tmp_path: Path):
    app = _build_app(tmp_path)
    client = app.test_client()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "ADMIN"
        session["session_token"] = "token"
        session["csrf_token"] = "csrf"

    secret_path = tmp_path / "runtime" / "config" / "aiplatform" / "deepseek.json"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    secret_path.write_text(json.dumps({"api_key": "kept-secret"}, ensure_ascii=False), encoding="utf-8")

    response = client.post(
        "/api/config/aiplatform/deepseek",
        json={
            "platform": "deepseek",
            "name": "DeepSeek",
            "description": "AI service",
            "icon": "/assets/aiplatform/deepseek.png",
            "enabled": True,
            "config": {
                "base_url": "https://api.deepseek.com/v1/chat/completions",
                "timeout": 45,
            },
            "models": [
                {
                    "id": "deepseek-chat",
                    "name": "DeepSeek Chat",
                    "description": "Chat model",
                    "enabled": True,
                },
            ],
        },
        headers={"X-CSRF-Token": "csrf"},
    )

    assert response.status_code == 200
    secret_text = secret_path.read_text(encoding="utf-8")
    assert "kept-secret" in secret_text


def test_platform_test_endpoint_uses_secret_store(tmp_path: Path, monkeypatch):
    app = _build_app(tmp_path)
    client = app.test_client()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "ADMIN"
        session["session_token"] = "token"
        session["csrf_token"] = "csrf"

    client.post(
        "/api/config/aiplatform/deepseek",
        json={
            "platform": "deepseek",
            "name": "DeepSeek",
            "description": "AI service",
            "icon": "/assets/aiplatform/deepseek.png",
            "enabled": True,
            "config": {
                "api_key": "request-secret",
                "base_url": "https://api.deepseek.com/v1/chat/completions",
                "timeout": 45,
            },
            "models": [
                {
                    "id": "deepseek-chat",
                    "name": "DeepSeek Chat",
                    "description": "Chat model",
                    "enabled": True,
                },
            ],
        },
        headers={"X-CSRF-Token": "csrf"},
    )

    captured = {}

    class DummyResponse:
        status_code = 200
        ok = True

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 3}}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trpg_server.routes.config.requests.post", fake_post)

    response = client.post(
        "/api/config/aiplatform/deepseek/test",
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hello"}]},
        headers={"X-CSRF-Token": "csrf"},
    )

    assert response.status_code == 200
    assert captured["headers"]["Authorization"] == "Bearer request-secret"
    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
