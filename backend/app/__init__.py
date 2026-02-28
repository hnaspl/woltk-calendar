"""Application factory."""

from __future__ import annotations

import logging

from flask import Flask, session
from flask_cors import CORS

from config import get_config
from app.extensions import bcrypt, db, login_manager, migrate


def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__)

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
        from flask import jsonify
        return jsonify({"error": "Authentication required"}), 401

    # --------------------------------------------------------- Blueprints
    from app.api.v1 import register_blueprints
    register_blueprints(app)

    # ------------------------------------------------- Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        from flask import jsonify
        return jsonify({"error": str(e.description) if hasattr(e, "description") else "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        from flask import jsonify
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        from flask import jsonify
        app.logger.exception("Unhandled 500 error: %s", e)
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        from flask import jsonify
        app.logger.exception("Unhandled exception: %s", e)
        return jsonify({"error": "Internal server error"}), 500

    # -------------------------------------------------- Health / root route
    @app.route("/")
    def index():
        from flask import jsonify
        return jsonify({"status": "ok", "app": "WotLK Calendar API", "version": "1.0.0"})

    @app.route("/api/v1/health")
    def health():
        from flask import jsonify
        return jsonify({"status": "ok"})

    # ------------------------------------------------------- CLI commands
    _register_commands(app)

    # --------------------------------------------------------- Scheduler
    with app.app_context():
        if app.config.get("SCHEDULER_ENABLED", True) and not app.config.get("TESTING", False):
            from app.jobs.scheduler import init_scheduler
            init_scheduler(app)

    return app


def _register_commands(app: Flask) -> None:
    import click

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, default=False, help="Drop and recreate all tables first.")
    def seed_command(reset: bool) -> None:
        """Seed the database with initial data."""
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
        db.create_all()
        click.echo("Database tables created.")
