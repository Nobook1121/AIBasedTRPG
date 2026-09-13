import logging
import subprocess
from pathlib import Path
import socket
import sys
import shutil

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from trpg_server.app_factory import create_app, socketio
from trpg_server.console_commands import start_console_command_loop
from trpg_server.network_discovery import (
    find_available_port,
    get_local_ip,
    get_local_ipv4_addresses,
    get_network_config,
    is_port_available,
)
from trpg_server.settings import DEFAULT_PORT

logger = logging.getLogger(__name__)

app = create_app()


def _iter_frontend_source_paths(root: Path):
    candidates = (
        root / "frontend" / "src",
        root / "frontend" / "src" / "templates",
        root / "frontend" / "src" / "index",
        root / "scripts" / "build-frontend.mjs",
        root / "scripts" / "relocate-tools.mjs",
        root / "package.json",
        root / "tsconfig.frontend.json",
        root / "tsconfig.react.json",
    )
    for path in candidates:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    yield child
        elif path.is_file():
            yield path


def _frontend_build_is_stale(root: Path) -> bool:
    outputs = [
        root / "dist" / "public" / "index.html",
        root / "dist" / "public" / "js" / "react" / "main.js",
        root / "dist" / "public" / "js" / "react" / "main.css",
    ]
    if any(not path.exists() for path in outputs):
        return True

    latest_source_mtime = max(path.stat().st_mtime for path in _iter_frontend_source_paths(root))
    oldest_output_mtime = min(path.stat().st_mtime for path in outputs)
    return latest_source_mtime > oldest_output_mtime


def ensure_frontend_build():
    root = Path(__file__).resolve().parent
    if not _frontend_build_is_stale(root):
        return
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise FileNotFoundError("npm is not available on PATH")
    subprocess.run([npm, "run", "build:frontend"], cwd=root, check=True)


def _log_listening_addresses(local_ip, port):
    for address in get_local_ipv4_addresses():
        logger.info("listening on http://%s:%s", address, port)


def _select_port(argv):
    config = get_network_config()
    port = config.get("port", DEFAULT_PORT)

    if len(argv) > 1:
        try:
            port = int(argv[1])
            logger.debug("Using command line port: %s", port)
        except ValueError:
            logger.warning("Invalid command line port; using configured port")

    if is_port_available(port):
        return port

    logger.warning("Port %s is in use; searching for an available port", port)
    available_port = find_available_port(port)
    if available_port:
        logger.debug("Found available port: %s", available_port)
        return available_port

    logger.error("No available port found; falling back to default port %s", DEFAULT_PORT)
    return DEFAULT_PORT


def run_server(argv=None):
    argv = argv or sys.argv
    port = _select_port(argv)
    local_ip = get_local_ip()
    ensure_frontend_build()
    logger.debug("Starting server on port %s", port)
    logger.debug("LAN URL: http://%s:%s", local_ip, port)
    _log_listening_addresses(local_ip, port)
    start_console_command_loop()

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

        logger.debug("Retrying server on port %s", available_port)
        _log_listening_addresses(local_ip, available_port)
        socketio.run(
            app,
            debug=False,
            host="0.0.0.0",
            port=available_port,
            allow_unsafe_werkzeug=True,
        )


if __name__ == "__main__":
    run_server()
