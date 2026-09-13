import logging
import subprocess
from pathlib import Path
import socket
import sys
import shutil
import threading
import secrets
import urllib.error
import urllib.request

from flask import abort, request
from werkzeug.serving import make_server

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from trpg_server.app_factory import create_app, socketio
from trpg_server.console_commands import set_shutdown_callback, start_console_command_loop
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

# A random, process-local token protects the internal stop endpoint.  The
# console command is the public control surface; the HTTP endpoint only exists
# so Flask-SocketIO can execute its server shutdown hook in request context.
_SHUTDOWN_TOKEN = secrets.token_urlsafe(32)
_shutdown_requested = threading.Event()
_http_server = None
_http_server_lock = threading.Lock()


@app.post("/__internal/shutdown")
def _internal_shutdown():
    if request.remote_addr not in {"127.0.0.1", "::1", "localhost"}:
        abort(404)
    if request.headers.get("X-TRPG-Shutdown-Token") != _SHUTDOWN_TOKEN:
        abort(403)
    if _shutdown_requested.is_set():
        return {"ok": True, "message": "Shutdown already requested"}

    _shutdown_requested.set()
    logger.info("Graceful shutdown accepted from local console")
    # ``werkzeug.server.shutdown`` was removed in recent Werkzeug releases.
    # Keep a reference to our WSGI server and stop it from a helper thread;
    # BaseServer.shutdown() must not be called by the request thread itself.
    with _http_server_lock:
        http_server = _http_server
    if http_server is not None:
        threading.Thread(target=http_server.shutdown, name="trpg-server-shutdown", daemon=True).start()
    else:
        try:
            socketio.stop()  # compatibility fallback for alternate runners
        except RuntimeError:
            logger.warning("Shutdown requested before the HTTP server was ready")
    return {"ok": True}


def _serve_http(port: int) -> None:
    """Run the Socket.IO-wrapped Flask app with a stoppable WSGI server."""

    global _http_server
    http_server = make_server("0.0.0.0", port, app, threaded=True)
    # Drain active request threads before closing the listening socket.
    http_server.daemon_threads = False
    http_server.block_on_close = True
    with _http_server_lock:
        _http_server = http_server
    try:
        http_server.serve_forever()
    finally:
        http_server.server_close()
        with _http_server_lock:
            if _http_server is http_server:
                _http_server = None


def _request_graceful_shutdown(port: int) -> None:
    """Ask the running server to stop through its loopback-only endpoint."""

    url = f"http://127.0.0.1:{port}/__internal/shutdown"
    request_obj = urllib.request.Request(
        url,
        method="POST",
        headers={"X-TRPG-Shutdown-Token": _SHUTDOWN_TOKEN},
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=5) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Unable to contact shutdown endpoint: %s", exc)


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
    _shutdown_requested.clear()
    port = _select_port(argv)
    local_ip = get_local_ip()
    ensure_frontend_build()
    logger.debug("Starting server on port %s", port)
    logger.debug("LAN URL: http://%s:%s", local_ip, port)
    _log_listening_addresses(local_ip, port)
    # Register the callback after the final port has been selected so the
    # console command always targets the actual listening socket.
    set_shutdown_callback(lambda: _request_graceful_shutdown(port))
    start_console_command_loop()

    try:
        _serve_http(port)
    except socket.error:
        logger.exception("Server failed to start on port %s", port)
        available_port = find_available_port(port)
        if not available_port:
            raise

        logger.debug("Retrying server on port %s", available_port)
        _log_listening_addresses(local_ip, available_port)
        set_shutdown_callback(lambda: _request_graceful_shutdown(available_port))
        _serve_http(available_port)


if __name__ == "__main__":
    run_server()
