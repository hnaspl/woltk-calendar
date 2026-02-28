"""Application factory."""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, send_from_directory, session
from flask_cors import CORS

from config import get_config
from app.extensions import bcrypt, db, login_manager, migrate

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
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)

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

    # --------------------------------------------------------- Scheduler
    with app.app_context():
        if app.config.get("SCHEDULER_ENABLED", True) and not app.config.get("TESTING", False):
            from app.jobs.scheduler import init_scheduler
            init_scheduler(app)

    return app


def _sync_schema() -> None:
    """Create missing tables and add missing columns to existing tables.

    ``db.create_all()`` only creates tables that do not exist yet; it will
    not ALTER existing tables.  This helper inspects every mapped table and
    issues ``ALTER TABLE … ADD COLUMN`` for any column that is defined in
    the model but absent from the live database, preventing
    "Unknown column" errors after schema changes.
    """
    import sqlalchemy as sa
    from sqlalchemy import inspect as sa_inspect

    db.create_all()

    inspector = sa_inspect(db.engine)
    for table_name, table_obj in db.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table_name)}
        for col in table_obj.columns:
            if col.name in existing:
                continue
            col_type = col.type.compile(dialect=db.engine.dialect)
            nullable = "" if col.nullable else " NOT NULL"
            default = ""
            if col.default is not None and not callable(getattr(col.default, "arg", None)):
                default = f" DEFAULT {col.default.arg!r}"
            elif not col.nullable and col.default is None:
                # Provide a safe zero-value so NOT NULL doesn't fail on
                # existing rows
                if isinstance(col.type, (sa.Boolean,)):
                    default = " DEFAULT 0"
                elif isinstance(col.type, (sa.Integer,)):
                    default = " DEFAULT 0"
                elif isinstance(col.type, (sa.String, sa.Text)):
                    default = " DEFAULT ''"
            stmt = f"ALTER TABLE `{table_name}` ADD COLUMN `{col.name}` {col_type}{nullable}{default}"
            db.session.execute(sa.text(stmt))
    db.session.commit()


def _register_commands(app: Flask) -> None:
    import click

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, default=False, help="Drop and recreate all tables first.")
    def seed_command(reset: bool) -> None:
        """Seed the database with initial data."""
        if reset:
            db.drop_all()
            click.echo("Dropped all tables.")
        _sync_schema()
        click.echo("Created all tables.")

        from app.seeds.raid_definitions import seed_raid_definitions
        inserted = seed_raid_definitions()
        click.echo(f"Seeded {inserted} raid definition(s).")

        from app.seeds.admin_user import seed_admin_user
        if seed_admin_user():
            click.echo("Created default admin user.")
        else:
            click.echo("Admin user already exists, skipped.")

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
        """Create all database tables and add any missing columns."""
        _sync_schema()
        click.echo("Database tables created.")
