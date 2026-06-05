from flask import Flask

from trpg_server.responses import error_response, success_response


def test_success_response_can_include_extra_fields_without_message():
    app = Flask(__name__)

    with app.app_context():
        response, status = success_response(message=None, response={"ok": True})

    assert status == 200
    assert response.get_json() == {"success": True, "response": {"ok": True}}


def test_error_response_can_include_error_without_message():
    app = Flask(__name__)

    with app.app_context():
        response, status = error_response(None, 502, "upstream failed")

    assert status == 502
    assert response.get_json() == {"success": False, "error": "upstream failed"}
