from trpg_server.app_factory import create_app, socketio


def _set_session(client, user_id=7, username="alice", token="token-7"):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["username"] = username
        session["role"] = "USER"
        session["session_token"] = token


def test_second_socket_connection_replaces_first_for_same_account():
    socketio._trpg_events_registered = False
    app = create_app()
    app.config["ACTIVE_USER_SESSIONS"] = {"7": "token-7"}
    first_http = app.test_client()
    second_http = app.test_client()
    _set_session(first_http)
    _set_session(second_http)

    first_socket = socketio.test_client(app, flask_test_client=first_http)
    assert first_socket.is_connected()
    first_sid = app.config["ACTIVE_SOCKET_SESSIONS"]["7"]

    second_socket = socketio.test_client(app, flask_test_client=second_http)
    second_sid = app.config["ACTIVE_SOCKET_SESSIONS"]["7"]

    assert second_socket.is_connected()
    assert second_sid != first_sid
