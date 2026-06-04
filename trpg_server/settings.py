import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

SCENARIOS_DIR = BASE_DIR / "scenarios"
SCENARIO_COVERS_DIR = BASE_DIR / "assets" / "scenario_covers"
AVATARS_DIR = BASE_DIR / "assets" / "avatars"
SAVES_DIR = BASE_DIR / "saves"
CONFIG_DIR = BASE_DIR / "config"
USERS_DIR = BASE_DIR / "users"
LOGS_DIR = BASE_DIR / "logs"

NETWORK_CONFIG_FILE = CONFIG_DIR / "network.json"
PENETRATION_CONFIG_FILE = CONFIG_DIR / "penetration.json"

DEFAULT_PORT = 8086
PORT_RETRY_COUNT = 5
PORT_RETRY_INTERVAL = 2
DISCOVERY_PORT = 50000
DISCOVERY_INTERVAL = 5

SECRET_KEY = os.environ.get("AI_TRPG_SECRET_KEY", "dev-only-change-me")
