"""ThreeOneOSFive-compatible local key & patch server.

Usage:
    python app.py                # http://127.0.0.1:5000
    ADMIN_KEY=... python app.py
"""
from flask import Flask, redirect, url_for

from config import config
from database import init_db
from admin import admin
from api import api


def create_app():
    init_db()
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024  # 512 MB per upload
    app.register_blueprint(api)
    app.register_blueprint(admin)

    @app.route("/")
    def index():
        return redirect(url_for("admin.dashboard"))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
