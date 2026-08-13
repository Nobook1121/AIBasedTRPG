import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
FRONTEND_DIST_DIR = BASE_DIR / "dist" / "public"

SCENARIOS_DIR = DATA_DIR / "scenarios"
CHARACTERS_DIR = RUNTIME_DIR / "characters"
SCENARIO_COVERS_DIR = DATA_DIR / "assets" / "scenario_covers"
AVATARS_DIR = DATA_DIR / "assets" / "avatars"
AI_PLATFORM_ASSETS_DIR = DATA_DIR / "assets" / "aiplatform"
VENDOR_ASSETS_DIR = DATA_DIR / "assets" / "vendor"
TOOLS_DIR = FRONTEND_DIST_DIR / "data" / "tools"
ROOMS_DIR = RUNTIME_DIR / "rooms"
CONFIG_DIR = DATA_DIR / "config"
OCCUPATIONS_DIR = DATA_DIR / "occupations"
WEAPONS_DIR = DATA_DIR / "weapons"
USERS_DIR = RUNTIME_DIR / "users"
HISTORY_DIR = RUNTIME_DIR / "history"
LOGS_DIR = RUNTIME_DIR / "logs"

NETWORK_CONFIG_FILE = CONFIG_DIR / "network.json"
PENETRATION_CONFIG_FILE = CONFIG_DIR / "penetration.json"

DEFAULT_PORT = 8086
PORT_RETRY_COUNT = 5
PORT_RETRY_INTERVAL = 2
DISCOVERY_PORT = 50000
DISCOVERY_INTERVAL = 5

SECRET_KEY = os.environ.get("AI_TRPG_SECRET_KEY", "dev-only-change-me")
