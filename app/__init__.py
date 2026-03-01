"""Application factory."""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, send_from_directory, session
from flask_cors import CORS

from config import get_config
from app.extensions import bcrypt, db, login_manager, socketio

# Vite build output directory (relative to project root)
DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")


def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")

    # ----------------------------------------------------------------- Config
    app.config.from_object(get_config())
    if config_override:
        app.config.update(config_override)

    # -------------------------------------------------------------- Logging
    logging.basicConfig(level=app.config.get("LOG_LEVEL", "INFO"))

    # ----------------------------------------------------------- Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config["CORS_ORIGINS"],
                      async_mode="gevent", logger=False, engineio_logger=False)

    # Enable WAL mode for SQLite (better concurrent read/write performance)
    if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        from sqlalchemy import event as sa_event
        from sqlalchemy.engine import Engine

        @sa_event.listens_for(Engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=True,
    )

    # ------------------------------------------------------- Flask-Login
    login_manager.session_protection = "basic"

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models.user import User
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Authentication required"}), 401

    # --------------------------------------------------------- Blueprints
    from app.api.v1 import register_blueprints
    register_blueprints(app)

    # ------------------------------------------------- Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": str(e.description) if hasattr(e, "description") else "Bad request"}), 400

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Unhandled 500 error: %s", e)
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception("Unhandled exception: %s", e)
        return jsonify({"error": "Internal server error"}), 500

    # ---------------------------------------- API health endpoint
    @app.route("/api/v1/health")
    def health():
        return jsonify({"status": "ok"})

    # ---------------------------------------- Serve Vue SPA
    @app.route("/")
    def serve_index():
        if os.path.isfile(os.path.join(DIST_DIR, "index.html")):
            return send_from_directory(DIST_DIR, "index.html")
        return jsonify({"status": "ok", "app": "WotLK Calendar API", "version": "1.0.0"})

    @app.errorhandler(404)
    def not_found(e):
        # API routes return JSON 404
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        # SPA client-side routing: serve index.html for non-API routes
        if os.path.isfile(os.path.join(DIST_DIR, "index.html")):
            return send_from_directory(DIST_DIR, "index.html")
        return jsonify({"error": "Not found"}), 404

    # ------------------------------------------------------- CLI commands
    _register_commands(app)

    # ------------------------------------------------------- SocketIO events
    _register_socketio_handlers()

    # --------------------------------------------------------- Scheduler
    with app.app_context():
        if app.config.get("SCHEDULER_ENABLED", True) and not app.config.get("TESTING", False):
            from app.jobs.scheduler import init_scheduler
            init_scheduler(app)

        # Seed default permission roles/permissions if tables are empty
        if not app.config.get("TESTING", False):
            _seed_permissions_if_empty(app)

    return app


def _ensure_db_dir() -> None:
    """Create the parent directory for file-based SQLite databases."""
    from flask import current_app

    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:///") and ":memory:" not in uri:
        db_path = uri.replace("sqlite:///", "", 1)
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)


def _register_socketio_handlers() -> None:
    """Register Socket.IO event handlers for room-based real-time updates."""
    from flask_login import current_user
    from flask_socketio import join_room, leave_room

    @socketio.on("join_event")
    def handle_join(data):
        if not current_user.is_authenticated:
            return
        event_id = data.get("event_id")
        if event_id is not None:
            join_room(f"event_{event_id}")

    @socketio.on("leave_event")
    def handle_leave(data):
        if not current_user.is_authenticated:
            return
        event_id = data.get("event_id")
        if event_id is not None:
            leave_room(f"event_{event_id}")

    @socketio.on("join_guild")
    def handle_join_guild(data):
        if not current_user.is_authenticated:
            return
        guild_id = data.get("guild_id")
        if guild_id is not None:
            join_room(f"guild_{guild_id}")

    @socketio.on("leave_guild")
    def handle_leave_guild(data):
        if not current_user.is_authenticated:
            return
        guild_id = data.get("guild_id")
        if guild_id is not None:
            leave_room(f"guild_{guild_id}")

    @socketio.on("connect")
    def handle_connect():
        """Auto-join the user's personal notification room on connect."""
        if current_user.is_authenticated:
            join_room(f"user_{current_user.id}")


def _seed_permissions_if_empty(app: Flask) -> None:
    """Seed default permission roles and permissions if tables are empty."""
    try:
        from app.models.permission import SystemRole
        import sqlalchemy as sa
        count = db.session.execute(
            sa.select(sa.func.count()).select_from(SystemRole)
        ).scalar()
        if count == 0:
            from app.seeds.permissions import seed_permissions
            created = seed_permissions()
            app.logger.info("Seeded %d default roles with permissions.", created)
    except Exception as exc:
        app.logger.warning("Failed to seed permissions: %s", exc)

    # Seed default system settings if missing
    try:
        from app.models.system_setting import SystemSetting
        defaults = {
            "wowhead_tooltips": "true",
            "autosync_enabled": "false",
            "autosync_interval_minutes": "60",
        }
        for key, default_value in defaults.items():
            existing = db.session.get(SystemSetting, key)
            if not existing:
                db.session.add(SystemSetting(key=key, value=default_value))
        db.session.commit()
    except Exception as exc:
        app.logger.warning("Failed to seed system settings: %s", exc)


def _register_commands(app: Flask) -> None:
    import click

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, default=False, help="Drop and recreate all tables first.")
    def seed_command(reset: bool) -> None:
        """Seed the database with initial data."""
        _ensure_db_dir()
        if reset:
            db.drop_all()
            click.echo("Dropped all tables.")
        db.create_all()
        click.echo("Created all tables.")

        from app.seeds.raid_definitions import seed_raid_definitions
        inserted = seed_raid_definitions()
        click.echo(f"Seeded {inserted} raid definition(s).")

        from app.seeds.admin_user import seed_admin_user
        if seed_admin_user():
            click.echo("Created default admin user.")
        else:
            click.echo("Admin user already exists, skipped.")

        from app.seeds.permissions import seed_permissions
        perm_count = seed_permissions()
        click.echo(f"Seeded {perm_count} role(s) with permissions.")

        from app.models.system_setting import SystemSetting
        defaults = {
            "wowhead_tooltips": "true",
            "autosync_enabled": "false",
            "autosync_interval_minutes": "60",
        }
        seeded_settings = 0
        for key, default_value in defaults.items():
            existing = db.session.get(SystemSetting, key)
            if not existing:
                db.session.add(SystemSetting(key=key, value=default_value))
                seeded_settings += 1
        db.session.commit()
        if seeded_settings:
            click.echo(f"Seeded {seeded_settings} system setting(s).")

    @app.cli.command("create-admin")
    @click.option("--email", default=None, help="Admin email (or set ADMIN_EMAIL env var).")
    @click.option("--username", default=None, help="Admin username (or set ADMIN_USERNAME env var).")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password.")
    def create_admin_command(email: str | None, username: str | None, password: str) -> None:
        """Create an admin user with the given credentials."""
        from app.seeds.admin_user import seed_admin_user
        if seed_admin_user(email=email, username=username, password=password):
            click.echo(f"Admin user created: {email or 'admin@wotlk-calendar.local'}")
        else:
            click.echo("User with that email or username already exists.")

    @app.cli.command("create-db")
    def create_db_command() -> None:
        """Create all database tables."""
        _ensure_db_dir()
        db.create_all()
        click.echo("Database tables created.")

        # Seed permissions if empty
        from app.models.permission import SystemRole
        import sqlalchemy as sa
        count = db.session.execute(
            sa.select(sa.func.count()).select_from(SystemRole)
        ).scalar()
        if count == 0:
            from app.seeds.permissions import seed_permissions
            created = seed_permissions()
            click.echo(f"Seeded {created} role(s) with permissions.")

        # Seed default system settings if missing
        from app.models.system_setting import SystemSetting
        defaults = {
            "wowhead_tooltips": "true",
            "autosync_enabled": "false",
            "autosync_interval_minutes": "60",
        }
        seeded_settings = 0
        for key, default_value in defaults.items():
            existing = db.session.get(SystemSetting, key)
            if not existing:
                db.session.add(SystemSetting(key=key, value=default_value))
                seeded_settings += 1
        db.session.commit()
        if seeded_settings:
            click.echo(f"Seeded {seeded_settings} system setting(s).")
