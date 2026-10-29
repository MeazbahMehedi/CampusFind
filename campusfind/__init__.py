"""Application factory and shared request policy."""

import json
import os
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

from .models import Notification, User, db

login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
CATEGORIES = [
    "Electronics",
    "Bags",
    "Keys",
    "Cards & IDs",
    "Books",
    "Clothing",
    "Accessories",
    "Other",
]
LOCATIONS = [
    "Central Library",
    "Teaching Building",
    "Cafeteria",
    "Sports Center",
    "Student Dormitory",
    "Campus Garden",
    "Other",
]
LABELS = {
    "reported": "Reported",
    "claim_pending": "Claim pending",
    "awaiting_handover": "Awaiting handover",
    "returned": "Returned",
    "closed": "Closed",
    "pending": "Pending review",
    "needs_info": "More information needed",
    "approved": "Approved",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
    "needs_changes": "Corrections requested",
    "published": "Published",
}


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    key_path = Path(app.instance_path) / "secret.key"
    key = os.getenv("SECRET_KEY")
    if not key:
        # Exclusive creation keeps concurrent workers from choosing different keys.
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w") as file:
                file.write(secrets.token_hex(32))
        key = key_path.read_text().strip()
    app.config.from_mapping(
        SECRET_KEY=key,
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL") or "sqlite:///campusfind.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        ADMIN_BOOTSTRAP_PATH=str(Path(app.instance_path) / "admin-bootstrap.json"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    csrf.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    app.jinja_env.globals["labels"] = LABELS

    from . import admin, auth, claims, cli, reports, views

    for blueprint in [views.bp, auth.bp, reports.bp, claims.bp, admin.bp]:
        app.register_blueprint(blueprint)
    cli.register(app)

    config_path = Path(app.root_path).parent / "config" / "developer.json"
    developer = json.loads(config_path.read_text(encoding="utf-8"))
    app.config["PROJECT_BRAND"] = developer
    for field in ["github_url", "linkedin_url", "website"]:
        value = developer.get(field, "")
        if value and urlsplit(value).scheme not in {"http", "https"}:
            raise ValueError(f"{field} must be an http(s) URL")
    for field in ["logo_path", "avatar_path"]:
        value = developer.get(field, "")
        if value and (value.startswith("/") or ".." in Path(value).parts or ":" in value):
            raise ValueError(f"{field} must be a relative static asset path")
    for person in developer.get("team", []):
        for field in ["github_url", "linkedin_url", "website"]:
            value = person.get(field, "")
            if value and urlsplit(value).scheme not in {"http", "https"}:
                raise ValueError(f"Team {field} must be an http(s) URL")
        value = person.get("avatar_path", "")
        if value and (value.startswith("/") or ".." in Path(value).parts or ":" in value):
            raise ValueError("Team avatar_path must be a relative static asset path")

    @app.context_processor
    def context():
        from .settings import campus_settings

        settings = campus_settings()
        unread = 0
        if current_user.is_authenticated:
            unread = db.session.scalar(
                db.select(db.func.count())
                .select_from(Notification)
                .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
            )
        return dict(
            brand=developer,
            categories=settings["categories"],
            locations=settings["locations"],
            campus=settings,
            labels=LABELS,
            unread_count=unread,
            version="1.2.0",
        )

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if current_user.is_authenticated or "auth." in (request.endpoint or ""):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template(
            "error.html", code=400, message="Your form expired. Refresh the page and try again."
        ), 400

    for code, message in [
        (400, "Please check your request and try again."),
        (403, "You do not have permission to open this page."),
        (404, "This page or item could not be found."),
        (413, "That upload is too large. Choose an image smaller than 5 MB."),
        (500, "Something went wrong. Please try again."),
    ]:

        def handler(error, code=code, message=message):
            if code == 500:
                db.session.rollback()
            return render_template("error.html", code=code, message=message), code

        app.register_error_handler(code, handler)
    return app


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.enabled else None


@login_manager.unauthorized_handler
def sign_in_required():
    endpoint = "auth.admin_login" if request.blueprint == "admin" else "auth.login"
    return redirect(url_for(endpoint, next=request.full_path.rstrip("?")))
