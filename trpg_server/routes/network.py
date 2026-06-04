import logging
import socket
import time

from flask import Blueprint, current_app, jsonify, request

from trpg_server.network_discovery import (
    DEFAULT_PORT,
    get_local_ip,
    get_network_config,
    get_penetration_config,
    save_network_config,
    save_penetration_config,
    test_udp_discovery,
)
from trpg_server.security import require_permission
from trpg_server.settings import NETWORK_CONFIG_FILE, PENETRATION_CONFIG_FILE

bp = Blueprint("network", __name__)
logger = logging.getLogger(__name__)


def _network_config_file():
    return current_app.config.get("NETWORK_CONFIG_FILE", NETWORK_CONFIG_FILE)


def _penetration_config_file():
    return current_app.config.get("PENETRATION_CONFIG_FILE", PENETRATION_CONFIG_FILE)


@bp.route("/api/network/config", methods=["GET"])
def get_network_config_api():
    try:
        config = get_network_config(_network_config_file())
        return jsonify(
            {
                "success": True,
                "data": config,
                "message": "Network config loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to get network config")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to get network config",
                }
            ),
            500,
        )


@bp.route("/api/network/config", methods=["POST"])
@require_permission("ADMIN")
def update_network_config_api():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide network config data",
                    }
                ),
                400,
            )

        validation_error = _validate_network_config(config_data)
        if validation_error:
            return validation_error

        saved_config = save_network_config(config_data, _network_config_file())
        logger.info("Network config updated port=%s", saved_config.get("port"))
        return jsonify(
            {
                "success": True,
                "data": config_data,
                "message": "Network config updated successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to update network config")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to update network config",
                }
            ),
            500,
        )


@bp.route("/api/network/status", methods=["GET"])
def get_network_status():
    try:
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            local_ip = "127.0.0.1"

        config = get_network_config(_network_config_file())
        port = config.get("port", DEFAULT_PORT)
        port_available = _can_bind(local_ip, port)
        status = {
            "local_ip": local_ip,
            "port": port,
            "port_available": port_available,
            "discovery_enabled": config.get("discovery_enabled", True),
            "access_control": config.get(
                "access_control",
                {"enabled": False, "allowed_ips": []},
            ),
            "timestamp": int(time.time()),
        }
        return jsonify(
            {
                "success": True,
                "data": status,
                "message": "Network status loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to get network status")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to get network status",
                }
            ),
            500,
        )


@bp.route("/api/network/test", methods=["POST"])
def test_network_connection():
    try:
        config = get_network_config(_network_config_file())
        local_ip = get_local_ip()
        target_port = config.get("port", DEFAULT_PORT)
        connection_success, error_message = _test_local_bind(local_ip)
        discovery_success, discovery_error = test_udp_discovery()

        return jsonify(
            {
                "success": True,
                "data": {
                    "local_ip": local_ip,
                    "port": target_port,
                    "connection_success": connection_success,
                    "error_message": error_message,
                    "discovery_success": discovery_success,
                    "discovery_error": discovery_error,
                },
                "message": "Network connection test completed",
            }
        )
    except Exception as exc:
        logger.exception("Failed to test network connection")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to test network connection",
                }
            ),
            500,
        )


@bp.route("/api/network/penetration/config", methods=["GET"])
@require_permission("ADMIN")
def get_penetration_config_api():
    try:
        config = get_penetration_config(_penetration_config_file())
        return jsonify(
            {
                "success": True,
                "data": config,
                "message": "Penetration config loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to get penetration config")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to get penetration config",
                }
            ),
            500,
        )


@bp.route("/api/network/penetration/config", methods=["POST"])
@require_permission("ADMIN")
def update_penetration_config_api():
    try:
        config_data = request.get_json(silent=True)
        if not config_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide penetration config data",
                    }
                ),
                400,
            )

        save_penetration_config(config_data, _penetration_config_file())
        logger.info("Penetration config updated type=%s", config_data.get("type"))
        return jsonify(
            {
                "success": True,
                "data": config_data,
                "message": "Penetration config updated successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to update penetration config")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to update penetration config",
                }
            ),
            500,
        )


@bp.route("/api/network/penetration/status", methods=["GET"])
def get_penetration_status():
    try:
        config = get_penetration_config(_penetration_config_file())
        status = {
            "enabled": config.get("enabled", False),
            "type": config.get("type", "ngrok"),
            "settings": config.get("settings", {}),
            "port_mappings": config.get("port_mappings", []),
            "timestamp": int(time.time()),
        }
        return jsonify(
            {
                "success": True,
                "data": status,
                "message": "Penetration status loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to get penetration status")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to get penetration status",
                }
            ),
            500,
        )


def _validate_network_config(config_data):
    port = config_data.get("port")
    if port:
        try:
            port = int(port)
            if port < 1 or port > 65535:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid port",
                            "message": "Port must be between 1 and 65535",
                        }
                    ),
                    400,
                )
        except (TypeError, ValueError):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid port",
                        "message": "Port must be an integer",
                    }
                ),
                400,
            )

    access_control = config_data.get("access_control", {})
    if access_control and isinstance(access_control, dict):
        allowed_ips = access_control.get("allowed_ips", [])
        if not isinstance(allowed_ips, list):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid config",
                        "message": "allowed_ips must be a list",
                    }
                ),
                400,
            )

    return None


def _can_bind(local_ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((local_ip, port))
        sock.close()
        return True
    except OSError:
        return False


def _test_local_bind(local_ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.bind((local_ip, 0))
        sock.close()
        return True, ""
    except socket.timeout:
        return False, "Connection timeout"
    except socket.gaierror:
        return False, "DNS resolution failed"
    except OSError as exc:
        return False, f"Network error: {exc}"
