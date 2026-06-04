import json
import logging
import socket
import time
from copy import deepcopy

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.settings import (
    DEFAULT_PORT,
    DISCOVERY_PORT,
    NETWORK_CONFIG_FILE,
    PENETRATION_CONFIG_FILE,
    PORT_RETRY_COUNT,
    PORT_RETRY_INTERVAL,
)

logger = logging.getLogger(__name__)

DEFAULT_NETWORK_CONFIG = {
    "port": DEFAULT_PORT,
    "discovery_enabled": True,
    "access_control": {
        "enabled": False,
        "allowed_ips": [],
    },
}

DEFAULT_PENETRATION_CONFIG = {
    "enabled": False,
    "type": "ngrok",
    "settings": {
        "auth_token": "",
        "region": "us",
        "subdomain": "",
    },
    "port_mappings": [],
}


def is_port_available(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("0.0.0.0", port))
        sock.close()
        return True
    except OSError:
        return False


def find_available_port(start_port, max_attempts=PORT_RETRY_COUNT):
    current_port = start_port
    attempts = 0
    while attempts < max_attempts:
        if is_port_available(current_port):
            return current_port
        attempts += 1
        current_port += 1
        time.sleep(PORT_RETRY_INTERVAL)
    return None


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except OSError:
        logger.exception("Failed to get local IP")
        return "127.0.0.1"


def get_network_config(path=NETWORK_CONFIG_FILE):
    data = read_json(path, default=None)
    if not data:
        return deepcopy(DEFAULT_NETWORK_CONFIG)
    return data


def save_network_config(config_data, path=NETWORK_CONFIG_FILE):
    current_config = get_network_config(path)
    current_config.update(config_data)
    write_json_atomic(path, current_config)
    return current_config


def get_penetration_config(path=PENETRATION_CONFIG_FILE):
    data = read_json(path, default=None)
    if not data:
        return deepcopy(DEFAULT_PENETRATION_CONFIG)
    return data


def save_penetration_config(config_data, path=PENETRATION_CONFIG_FILE):
    current_config = get_penetration_config(path)
    current_config.update(config_data)
    write_json_atomic(path, current_config)
    return current_config


def test_udp_discovery():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2)
        sock.sendto(json.dumps({"test": "discovery"}).encode("utf-8"), ("<broadcast>", DISCOVERY_PORT))
        sock.close()
        return True, ""
    except OSError as exc:
        return False, str(exc)
