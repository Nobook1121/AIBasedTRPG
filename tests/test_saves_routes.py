from trpg_server.app_factory import create_app


def _saves_app(tmp_path):
    saves_dir = tmp_path / "saves"
    app = create_app()
    app.config["SAVES_DIR"] = saves_dir
    return app, saves_dir


def _create_save(client, name="Run One"):
    response = client.post(
        "/api/saves",
        json={"name": name, "scenario_id": 12, "scenario_title": "Scenario"},
    )
    assert response.status_code == 201
    return response.get_json()["data"]


def test_saves_create_and_list(tmp_path):
    app, saves_dir = _saves_app(tmp_path)
    client = app.test_client()

    save_info = _create_save(client)
    response = client.get("/api/saves")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"][0]["id"] == save_info["id"]
    assert (saves_dir / "Run One" / "info.json").exists()
    assert (saves_dir / "Run One" / "autosave.json").exists()


def test_saves_create_list_and_load_node(tmp_path):
    app, _ = _saves_app(tmp_path)
    client = app.test_client()
    save_info = _create_save(client)

    response = client.post(
        f"/api/saves/{save_info['id']}/nodes",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["messages"][0]["content"] == "hello"

    nodes_response = client.get(f"/api/saves/{save_info['id']}/nodes")
    assert nodes_response.status_code == 200
    nodes = nodes_response.get_json()["data"]["nodes"]
    assert nodes[0]["message_count"] == 1

    load_response = client.get(
        f"/api/saves/{save_info['id']}/nodes/{nodes[0]['filename']}"
    )
    assert load_response.status_code == 200
    assert load_response.get_json()["data"]["messages"][0]["content"] == "hello"


def test_saves_autosave_round_trip(tmp_path):
    app, _ = _saves_app(tmp_path)
    client = app.test_client()
    save_info = _create_save(client)

    save_response = client.post(
        f"/api/saves/{save_info['id']}/autosave",
        json={"messages": [{"role": "assistant", "content": "saved"}]},
    )
    assert save_response.status_code == 200

    load_response = client.get(f"/api/saves/{save_info['id']}/autosave")
    assert load_response.status_code == 200
    assert load_response.get_json()["data"]["messages"][0]["content"] == "saved"


def test_saves_delete_save(tmp_path):
    app, saves_dir = _saves_app(tmp_path)
    client = app.test_client()
    save_info = _create_save(client)

    response = client.delete(f"/api/saves/{save_info['id']}")

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert not (saves_dir / "Run One").exists()
