from flask import jsonify


def success_response(data=None, message="success", status=200, **extra):
    payload = {"success": True}
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload), status


def error_response(message, status=400, error=None, **extra):
    payload = {"success": False}
    if message is not None:
        payload["message"] = message
    if error:
        payload["error"] = error
    payload.update(extra)
    return jsonify(payload), status
