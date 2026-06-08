import logging

from flask import current_app, request, session
from flask_socketio import disconnect, emit, join_room, leave_room

from trpg_server.security import ACTIVE_SESSION_REGISTRY_KEY, SESSION_TOKEN_KEY

logger = logging.getLogger(__name__)


def register_socket_events(socketio):
    if getattr(socketio, "_trpg_events_registered", False):
        return

    def _session_is_current():
        if "user_id" not in session:
            return False
        active_sessions = current_app.config.setdefault(ACTIVE_SESSION_REGISTRY_KEY, {})
        active_token = active_sessions.get(str(session["user_id"]))
        return not active_token or session.get(SESSION_TOKEN_KEY) == active_token

    def _replace_active_socket():
        active_sockets = current_app.config.setdefault("ACTIVE_SOCKET_SESSIONS", {})
        user_key = str(session["user_id"])
        previous_sid = active_sockets.get(user_key)
        if previous_sid and previous_sid != request.sid:
            socketio.emit("session_expired", room=f"user:{user_key}", namespace="/")
        active_sockets[user_key] = request.sid

    @socketio.on("connect")
    def handle_connect():
        if not _session_is_current():
            emit("session_expired")
            disconnect()
            return False
        _replace_active_socket()
        join_room(f"user:{session['user_id']}")
        logger.debug("WebSocket client connected user_id=%s", session.get("user_id"))

    @socketio.on("disconnect")
    def handle_disconnect():
        if "user_id" in session:
            active_sockets = current_app.config.setdefault("ACTIVE_SOCKET_SESSIONS", {})
            user_key = str(session["user_id"])
            if active_sockets.get(user_key) == request.sid:
                active_sockets.pop(user_key, None)
        logger.debug("WebSocket client disconnected")

    @socketio.on("join_room")
    def handle_join_room(data):
        if not _session_is_current():
            emit("session_expired")
            disconnect()
            return

        room_id = (data or {}).get("room_id")
        if room_id:
            join_room(room_id)
            logger.debug("WebSocket room joined room_id=%s user_id=%s", room_id, session.get("user_id"))

    @socketio.on("leave_room")
    def handle_leave_room(data):
        room_id = (data or {}).get("room_id")
        if room_id:
            leave_room(room_id)
            logger.debug("WebSocket room left room_id=%s user_id=%s", room_id, session.get("user_id"))

    @socketio.on("send_message")
    def handle_send_message(data):
        if not _session_is_current():
            emit("session_expired")
            disconnect()
            return

        payload = data or {}
        message = payload.get("message") or payload
        room_id = payload.get("room_id")
        logger.info(
            "WebSocket message received room_id=%s sender=%s type=%s",
            room_id,
            message.get("sender_name") or message.get("sender"),
            message.get("type"),
        )
        if room_id:
            emit("new_message", payload, room=room_id, include_self=False)
        else:
            emit("new_message", payload, broadcast=True, include_self=False)

    @socketio.on("typing")
    def handle_typing(data):
        if not _session_is_current():
            emit("session_expired")
            disconnect()
            return

        room_id = (data or {}).get("room_id")
        if room_id:
            emit("user_typing", data, room=room_id, include_self=False)
        else:
            emit("user_typing", data, broadcast=True, include_self=False)

    socketio._trpg_events_registered = True
