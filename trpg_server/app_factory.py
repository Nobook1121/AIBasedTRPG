from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from trpg_server.logging_config import configure_logging, register_request_logging
from trpg_server.socket_events import register_socket_events
from trpg_server.settings import SECRET_KEY

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    configure_logging()
    app = Flask(__name__, static_folder="../assets", static_url_path="/assets")
    app.secret_key = SECRET_KEY
    CORS(app)
    socketio.init_app(app)
    register_request_logging(app)
    register_blueprints(app)
    register_socket_events(socketio)
    return app


def register_blueprints(app):
    from trpg_server.routes.pages import bp as pages_bp

    app.register_blueprint(pages_bp)
