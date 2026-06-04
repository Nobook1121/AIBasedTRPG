from flask import jsonify


def success_response(data=None, message="success", status=200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def error_response(message, status=400, error=None):
    payload = {"success": False, "message": message}
    if error:
        payload["error"] = error
    return jsonify(payload), status
