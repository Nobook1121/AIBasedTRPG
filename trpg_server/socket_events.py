import logging

from flask_socketio import emit

logger = logging.getLogger(__name__)


def register_socket_events(socketio):
    if getattr(socketio, "_trpg_events_registered", False):
        return

    @socketio.on("connect")
    def handle_connect():
        logger.info("WebSocket client connected")

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.info("WebSocket client disconnected")

    @socketio.on("send_message")
    def handle_send_message(data):
        logger.info("WebSocket message received")
        emit("new_message", data, broadcast=True, include_self=False)

    @socketio.on("typing")
    def handle_typing(data):
        emit("user_typing", data, broadcast=True, include_self=False)

    socketio._trpg_events_registered = True
