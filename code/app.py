# app.py
from flask import Flask
from flask_cors import CORS
import logging
from config import Settings
from routes.api import api_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Settings())

    # Logging
    logging.basicConfig(level=app.config["LOG_LEVEL"])

    # CORS
    CORS(app)

    # Blueprints
    app.register_blueprint(api_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(
        debug=app.config["DEBUG"],
        host=app.config["HOST"],
        port=app.config["PORT"]
    )
