from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from trpg_server.logging_config import configure_logging, register_request_logging
from trpg_server.socket_events import register_socket_events
from trpg_server.settings import SECRET_KEY

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    configure_logging()
    app = Flask(__name__, static_folder=None)
    app.secret_key = SECRET_KEY
    CORS(app)
    socketio.init_app(app)
    register_request_logging(app)
    register_blueprints(app)
    register_socket_events(socketio)
    return app


def register_blueprints(app):
    from trpg_server.routes.assets import bp as assets_bp
    from trpg_server.routes.auth import bp as auth_bp
    from trpg_server.routes.pages import bp as pages_bp
    from trpg_server.routes.scenarios import bp as scenarios_bp
    from trpg_server.routes.users import bp as users_bp

    app.register_blueprint(assets_bp)
    app.register_blueprint(scenarios_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(pages_bp)
