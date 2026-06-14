from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import timedelta
import logging
import sqlite3

from trpg_server.logging_config import configure_logging
from trpg_server.security import register_session_guard
from trpg_server.socket_events import register_socket_events
from trpg_server.settings import LOGS_DIR, SECRET_KEY, USERS_DIR
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
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
        USER_DATABASE_FILE=USERS_DIR / "users.sqlite3",
        USERS_FILE=USERS_DIR / "users.json",
        USER_IP_CONFIG_DIR=USERS_DIR / "ip_configs",
    )
    if config:
        app.config.update(config)
    configure_logging(app.config.get("LOGS_DIR", LOGS_DIR))
    _configure_user_service(app)
    CORS(app)
    socketio.init_app(app)
    register_session_guard(app)
    register_blueprints(app)
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
    from trpg_server.routes.pages import bp as pages_bp
    from trpg_server.routes.rooms import bp as rooms_bp
    from trpg_server.routes.scenarios import bp as scenarios_bp
    from trpg_server.routes.users import bp as users_bp

    app.register_blueprint(assets_bp)
    app.register_blueprint(scenarios_bp)
    app.register_blueprint(characters_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(pages_bp)
