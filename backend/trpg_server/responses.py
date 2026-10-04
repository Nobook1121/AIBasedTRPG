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


SERVER_ERROR_MESSAGE = "Internal server error"


def server_error(message=None):
    """500 响应的统一出口。

    调用方必须已在对应的 except 分支里用 logger.exception 记录内部异常；
    这里只保证客户端拿到稳定的通用文案，不回传异常文本、文件路径、SQL
    或上游响应等内部细节，避免信息泄露。
    """
    return error_response(message or SERVER_ERROR_MESSAGE, 500, SERVER_ERROR_MESSAGE)
