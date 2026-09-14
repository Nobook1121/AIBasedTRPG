import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
FRONTEND_DIST_DIR = BASE_DIR / "dist" / "public"

SCENARIOS_DIR = DATA_DIR / "scenarios"
SCENARIO_DRAFTS_DIR = RUNTIME_DIR / "scenario_drafts"
CHARACTERS_DIR = RUNTIME_DIR / "characters"
CHARACTER_GALLERY_DIR = RUNTIME_DIR / "character_gallery"
SCENARIO_COVERS_DIR = DATA_DIR / "assets" / "scenario_covers"
AVATARS_DIR = DATA_DIR / "assets" / "avatars"
AI_PLATFORM_ASSETS_DIR = DATA_DIR / "assets" / "aiplatform"
VENDOR_ASSETS_DIR = DATA_DIR / "assets" / "vendor"
TOOLS_DIR = FRONTEND_DIST_DIR / "data" / "tools"
ROOMS_DIR = RUNTIME_DIR / "rooms"
CONFIG_DIR = DATA_DIR / "config"
DEBUG_KP_PROMPT_FILE = CONFIG_DIR / "roles" / "debug-kp.md"
AI_PLATFORM_SECRET_DIR = RUNTIME_DIR / "config" / "aiplatform"
OCCUPATIONS_DIR = DATA_DIR / "occupations"
WEAPONS_DIR = DATA_DIR / "weapons"
USERS_DIR = RUNTIME_DIR / "users"
HISTORY_DIR = RUNTIME_DIR / "history"
LOGS_DIR = RUNTIME_DIR / "logs"
KNOWLEDGE_BASES_DIR = RUNTIME_DIR / "knowledge-bases"

NETWORK_CONFIG_FILE = CONFIG_DIR / "network.json"
PENETRATION_CONFIG_FILE = CONFIG_DIR / "penetration.json"

DEFAULT_PORT = 8086
PORT_RETRY_COUNT = 5
PORT_RETRY_INTERVAL = 2
DISCOVERY_PORT = 50000
DISCOVERY_INTERVAL = 5

def _load_secret_key() -> str:
    env_secret = os.environ.get("AI_TRPG_SECRET_KEY")
    if env_secret:
        return env_secret

    secret_file = RUNTIME_DIR / "flask_secret_key.txt"
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()

    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_key = secrets.token_urlsafe(64)
    secret_file.write_text(secret_key, encoding="utf-8")
    return secret_key


SECRET_KEY = _load_secret_key()
SESSION_COOKIE_SECURE = os.environ.get("AI_TRPG_SESSION_COOKIE_SECURE", "0").strip().lower() in {"1", "true", "yes"}
