"""Application factory: configuration, request security and database lifecycle."""

import os
import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path
from flask import Flask, g, jsonify, request, session, render_template
from dotenv import load_dotenv


def create_app(test_config=None):
    load_dotenv()
    root = Path(__file__).resolve().parent.parent
    instance = root / "instance"
    instance.mkdir(exist_ok=True)
    secret_file = instance / ".secret"
    if not secret_file.exists():
        try:
            with secret_file.open("x") as f:
                f.write(secrets.token_hex(32))
            secret_file.chmod(0o600)
        except FileExistsError:
            pass
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY") or secret_file.read_text(),
        DATABASE=str(instance / "clinic.db"),
        INSTANCE_DIR=str(instance),
        CLINIC_TIMEZONE="Asia/Karachi",
        BASE_URL=os.getenv("BASE_URL", "http://127.0.0.1:5000"),
        MAIL_MODE=os.getenv("MAIL_MODE", "file"),
        SMTP_HOST=os.getenv("SMTP_HOST", ""),
        SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_USER=os.getenv("SMTP_USER", ""),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        SMTP_FROM=os.getenv("SMTP_FROM", "clinic@localhost"),
        SMTP_TLS=os.getenv("SMTP_TLS", "true").lower() == "true",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=32 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    from .db import db
    from .domain import Problem
    from .routes import api

    app.register_blueprint(api)
    with app.app_context():
        db().executescript((root / "app/schema.sql").read_text())

    @app.before_request
    def security():
        if request.path.startswith("/api/"):
            session.setdefault("csrf", secrets.token_urlsafe(32))
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                if not secrets.compare_digest(
                    request.headers.get("X-CSRF-Token", ""), session["csrf"]
                ):
                    raise Problem(
                        "Security token expired. Refresh the page and try again.", 403
                    )
                db().execute("BEGIN IMMEDIATE")
            g.user = (
                db()
                .execute(
                    "SELECT * FROM users WHERE id=? AND active=1", (session.get("uid"),)
                )
                .fetchone()
            )

    @app.after_request
    def headers(response):
        if "db" in g and g.db.in_transaction:
            if response.status_code < 400:
                g.db.commit()
            else:
                g.db.rollback()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.teardown_appcontext
    def close(error=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.errorhandler(Problem)
    def problem(error):
        return jsonify(error=error.message), error.status

    @app.errorhandler(sqlite3.IntegrityError)
    def conflict(error):
        return (
            jsonify(
                error="This slot or account is already taken. Refresh and choose another."
            ),
            409,
        )

    @app.errorhandler(400)
    def bad_request(error):
        return (
            jsonify(error="Please send valid JSON and complete the required fields."),
            400,
        )

    @app.errorhandler(500)
    def server_error(error):
        return jsonify(error="Something went wrong. Please try again."), 500

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        db().execute("SELECT 1")
        return {"status": "healthy"}

    return app
