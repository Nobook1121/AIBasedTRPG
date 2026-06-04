from trpg_server.app_factory import create_app


def test_create_app_serves_index_page():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


def test_create_app_serves_avatar_with_no_cache_headers():
    app = create_app()
    client = app.test_client()

    response = client.get("/assets/avatars/default.jpg")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"
