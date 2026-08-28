import os
from pathlib import Path

from flask import Flask, current_app, jsonify, send_from_directory

from app.database import close_db, init_db


def create_app(test_config=None):
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    root_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        static_folder=str(root_dir / "static"),
        static_url_path="",
    )
    app.config.from_mapping(
        DATABASE_PATH=root_dir / "instance" / "report_it.sqlite3",
        UPLOAD_FOLDER=root_dir / "instance" / "uploads",
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-5.6"),
        MAX_UPLOAD_BYTES=5 * 1024 * 1024,
        RATE_LIMIT_MAX=12,
        RATE_LIMIT_WINDOW_SECONDS=60,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db()

    from app.routes import api

    app.register_blueprint(api)
    app.teardown_appcontext(close_db)

    @app.get("/")
    def index():
        return send_from_directory(current_app.static_folder, "index.html")

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "error": "Not found"}), 404

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response

    return app
