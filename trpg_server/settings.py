import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

SCENARIOS_DIR = DATA_DIR / "scenarios"
CHARACTERS_DIR = DATA_DIR / "characters"
SCENARIO_COVERS_DIR = DATA_DIR / "assets" / "scenario_covers"
AVATARS_DIR = DATA_DIR / "assets" / "avatars"
ROOMS_DIR = DATA_DIR / "rooms"
CONFIG_DIR = DATA_DIR / "config"
USERS_DIR = DATA_DIR / "users"
HISTORY_DIR = DATA_DIR / "history"
LOGS_DIR = DATA_DIR / "logs"

NETWORK_CONFIG_FILE = CONFIG_DIR / "network.json"
PENETRATION_CONFIG_FILE = CONFIG_DIR / "penetration.json"

DEFAULT_PORT = 8086
PORT_RETRY_COUNT = 5
PORT_RETRY_INTERVAL = 2
DISCOVERY_PORT = 50000
DISCOVERY_INTERVAL = 5

SECRET_KEY = os.environ.get("AI_TRPG_SECRET_KEY", "dev-only-change-me")
