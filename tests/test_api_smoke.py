from server import app


def test_index_serves_html():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


def test_scenarios_endpoint_returns_json_shape():
    client = app.test_client()

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    data = response.get_json()
    assert "success" in data
    assert "data" in data
