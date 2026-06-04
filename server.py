import logging
import socket
import sys

from trpg_server.app_factory import create_app, socketio
from trpg_server.network_discovery import (
    find_available_port,
    get_local_ip,
    get_network_config,
    is_port_available,
)
from trpg_server.settings import DEFAULT_PORT

logger = logging.getLogger(__name__)

app = create_app()


def _select_port(argv):
    config = get_network_config()
    port = config.get("port", DEFAULT_PORT)

    if len(argv) > 1:
        try:
            port = int(argv[1])
            logger.info("Using command line port: %s", port)
        except ValueError:
            logger.warning("Invalid command line port; using configured port")

    if is_port_available(port):
        return port

    logger.warning("Port %s is in use; searching for an available port", port)
    available_port = find_available_port(port)
    if available_port:
        logger.info("Found available port: %s", available_port)
        return available_port

    logger.error("No available port found; falling back to default port %s", DEFAULT_PORT)
    return DEFAULT_PORT


def run_server(argv=None):
    argv = argv or sys.argv
    port = _select_port(argv)
    local_ip = get_local_ip()
    logger.info("Starting server on port %s", port)
    logger.info("LAN URL: http://%s:%s", local_ip, port)

    try:
        socketio.run(
            app,
            debug=False,
            host="0.0.0.0",
            port=port,
            allow_unsafe_werkzeug=True,
        )
    except socket.error:
        logger.exception("Server failed to start on port %s", port)
        available_port = find_available_port(port)
        if not available_port:
            raise

        logger.info("Retrying server on port %s", available_port)
        socketio.run(
            app,
            debug=False,
            host="0.0.0.0",
            port=available_port,
            allow_unsafe_werkzeug=True,
        )


if __name__ == "__main__":
    run_server()
