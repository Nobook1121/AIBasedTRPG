from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import timedelta
import logging
import sqlite3
import os
from pathlib import Path

from trpg_server.logging_config import configure_logging
from trpg_server.security import register_session_guard
from trpg_server.socket_events import register_socket_events
from trpg_server.settings import LOGS_DIR, SECRET_KEY, SESSION_COOKIE_SECURE, USERS_DIR, WEAPONS_DIR
from trpg_server.settings import SCENARIO_IMPORTS_DIR, SCENARIO_IMPORT_MAX_BYTES, SCENARIO_IMPORT_WORKERS
from trpg_server.settings import VECTOR_DB_URL, VECTOR_DB_PATH, VECTOR_DB_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, OCR_ENABLED, OCR_LANG, LOCAL_EMBEDDING_MODEL_PATH, PADDLEOCR_HOME, AI_PLATFORM_SECRET_DIR, CONFIG_DIR
from trpg_server.agents.vector_store import QdrantVectorStore
from trpg_server.agents.embedding_provider import select_embedding_provider
from trpg_server.ai_platform_config import load_platform_config
from trpg_server.agents.ocr_provider import PaddleOcrProvider
from trpg_server.scenario_import_jobs import ImportJobStore
from concurrent.futures import ThreadPoolExecutor
from trpg_server.users.database import UserDatabase
from trpg_server.users.migrations import migrate_json_users
from trpg_server.users.service import UserService

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.secret_key = SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
        USER_DATABASE_FILE=USERS_DIR / "users.sqlite3",
        USERS_FILE=USERS_DIR / "users.json",
        USER_IP_CONFIG_DIR=USERS_DIR / "ip_configs",
        WEAPONS_DIR=WEAPONS_DIR,
        SCENARIO_IMPORTS_DIR=SCENARIO_IMPORTS_DIR,
        SCENARIO_IMPORT_MAX_BYTES=SCENARIO_IMPORT_MAX_BYTES,
        SCENARIO_IMPORT_WORKERS=SCENARIO_IMPORT_WORKERS,
        VECTOR_DB_URL=VECTOR_DB_URL, VECTOR_DB_PATH=VECTOR_DB_PATH, VECTOR_DB_API_KEY=VECTOR_DB_API_KEY,
        EMBEDDING_BASE_URL=EMBEDDING_BASE_URL, EMBEDDING_API_KEY=EMBEDDING_API_KEY, EMBEDDING_MODEL=EMBEDDING_MODEL,
        EMBEDDING_DIMENSIONS=EMBEDDING_DIMENSIONS, OCR_ENABLED=OCR_ENABLED, OCR_LANG=OCR_LANG,
        LOCAL_EMBEDDING_MODEL_PATH=LOCAL_EMBEDDING_MODEL_PATH,
    )
    if config:
        app.config.update(config)
    configure_logging(app.config.get("LOGS_DIR", LOGS_DIR))
    if "USER_MANAGER" not in app.config:
        _configure_user_service(app)
    CORS(app)
    socketio.init_app(app)
    register_session_guard(app)
    register_blueprints(app)
    app.extensions["scenario_import_store"] = ImportJobStore(app.config["SCENARIO_IMPORTS_DIR"])
    app.extensions["scenario_import_store"].recover_interrupted()
    app.extensions["scenario_import_executor"] = ThreadPoolExecutor(max_workers=app.config["SCENARIO_IMPORT_WORKERS"])
    embedding_url, embedding_key, embedding_model, embedding_dimensions = app.config["EMBEDDING_BASE_URL"], app.config["EMBEDDING_API_KEY"], app.config["EMBEDDING_MODEL"], app.config["EMBEDDING_DIMENSIONS"]
    if not (embedding_url and embedding_key and embedding_model):
        platform_dir = Path(app.config.get("AI_PLATFORM_DIR", CONFIG_DIR / "aiplatform"))
        secret_dir = Path(app.config.get("AI_PLATFORM_SECRET_DIR", AI_PLATFORM_SECRET_DIR))
        for public_path in sorted(platform_dir.glob("*.json")):
            candidate = load_platform_config(public_path, secret_dir / public_path.name)
            embedding = candidate.get("embedding") if isinstance(candidate.get("embedding"), dict) else {}
            key = candidate.get("config", {}).get("api_key")
            if candidate.get("enabled") and embedding.get("base_url") and embedding.get("model") and key:
                embedding_url, embedding_key, embedding_model = embedding["base_url"], key, embedding["model"]
                embedding_dimensions = int(embedding.get("dimensions") or embedding_dimensions)
                break
    app.extensions["embedding_provider"] = select_embedding_provider(local_model_path=app.config["LOCAL_EMBEDDING_MODEL_PATH"], base_url=embedding_url, api_key=embedding_key, model=embedding_model, dimensions=embedding_dimensions)
    provider_dimensions = getattr(app.extensions["embedding_provider"], "dimensions", None) or embedding_dimensions
    app.extensions["vector_store"] = QdrantVectorStore(app.config["VECTOR_DB_URL"], str(app.config["VECTOR_DB_PATH"]), app.config["VECTOR_DB_API_KEY"], provider_dimensions)
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PADDLEOCR_HOME))
    app.extensions["ocr_provider"] = PaddleOcrProvider(app.config["OCR_LANG"]) if app.config["OCR_ENABLED"] else None
    app.config["OCR_PROVIDER"] = app.extensions["ocr_provider"]
    app.config["EMBEDDING_PROVIDER"] = app.extensions["embedding_provider"]
    app.config["VECTOR_STORE"] = app.extensions["vector_store"]
    register_socket_events(socketio)
    return app


def _configure_user_service(app):
    db = UserDatabase(app.config["USER_DATABASE_FILE"])
    db.initialize()
    try:
        migrate_json_users(app.config["USERS_FILE"], db)
    except (ValueError, sqlite3.Error):
        logger.exception("Skipping legacy user migration because users JSON is invalid")
    app.config["USER_MANAGER"] = UserService(
        db,
        ip_config_dir=app.config["USER_IP_CONFIG_DIR"],
    )


def register_blueprints(app):
    from trpg_server.routes.assets import bp as assets_bp
    from trpg_server.routes.auth import bp as auth_bp
    from trpg_server.routes.chat import bp as chat_bp
    from trpg_server.routes.characters import bp as characters_bp
    from trpg_server.routes.config import bp as config_bp
    from trpg_server.routes.network import bp as network_bp
    from trpg_server.routes.knowledge_bases import bp as knowledge_bases_bp
    from trpg_server.routes.pages import bp as pages_bp
    from trpg_server.routes.rooms import bp as rooms_bp
    from trpg_server.routes.scenarios import bp as scenarios_bp
    from trpg_server.routes.scenario_imports import bp as scenario_imports_bp
    from trpg_server.routes.vector_health import bp as vector_health_bp
    from trpg_server.routes.telemetry import bp as telemetry_bp
    from trpg_server.routes.users import bp as users_bp

    app.register_blueprint(assets_bp)
    app.register_blueprint(scenarios_bp)
    app.register_blueprint(scenario_imports_bp)
    app.register_blueprint(vector_health_bp)
    app.register_blueprint(characters_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(knowledge_bases_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(telemetry_bp)
