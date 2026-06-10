from trpg_server.app_factory import create_app


def test_chat_uses_role_config_wake_word_prompt_and_provider(tmp_path, monkeypatch):
    platform_dir = tmp_path / "aiplatform"
    platform_dir.mkdir()
    (platform_dir / "alpha.json").write_text(
        """
        {
          "enabled": true,
          "config": {"api_key": "alpha-key", "base_url": "http://alpha.local/chat"},
          "models": [{"id": "alpha-model", "enabled": true}]
        }
        """,
        encoding="utf-8",
    )
    (platform_dir / "beta.json").write_text(
        """
        {
          "enabled": true,
          "config": {"api_key": "beta-key", "base_url": "http://beta.local/chat"},
          "models": [{"id": "beta-model", "enabled": true}]
        }
        """,
        encoding="utf-8",
    )
    role_config = tmp_path / "roles.json"
    role_config.write_text(
        """
        {
          "roles": [
            {
              "id": "narrator",
              "name": "Narrator",
              "wake_words": ["@Narrator"],
              "prompt": "你是旁白",
              "provider": "beta"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    captured = {}

    class Response:
        ok = True
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "旁白回应"}}]}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return Response()

    monkeypatch.setattr("trpg_server.routes.chat.requests.post", fake_post)
    app = create_app(
        {
            "AI_PLATFORM_DIR": platform_dir,
            "ROLE_CONFIG_FILE": role_config,
            "HISTORY_DIR": tmp_path / "history",
            "USER_DATABASE_FILE": tmp_path / "users.sqlite3",
            "USERS_FILE": tmp_path / "users.json",
        }
    )
    client = app.test_client()

    response = client.post("/api/chat", json={"user_id": "u1", "content": "@Narrator 描述房间"})

    assert response.status_code == 200
    assert captured["url"] == "http://beta.local/chat"
    assert captured["headers"]["Authorization"] == "Bearer beta-key"
    assert captured["json"]["model"] == "beta-model"
    assert captured["json"]["messages"][0] == {"role": "system", "content": "你是旁白"}
