"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from datetime import timedelta


class Config:
    # ------------------------------------------------------------------ Flask
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG: bool = False
    TESTING: bool = False

    # -------------------------------------------------------------- Database
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "instance", "wotlk_calendar.db"
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "connect_args": {"timeout": 20},
        "pool_pre_ping": True,
    }

    # --------------------------------------------------------------- Session
    SESSION_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        seconds=int(os.environ.get("PERMANENT_SESSION_LIFETIME", "86400"))
    )

    # --------------------------------------------------------- Remember cookie
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_SAMESITE: str = "Lax"
    REMEMBER_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"  # mirrors session cookie

    # ------------------------------------------------------------------ CORS
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    # ----------------------------------------------------------- APScheduler
    SCHEDULER_ENABLED: bool = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
    SCHEDULER_TIMEZONE: str = os.environ.get("SCHEDULER_TIMEZONE", "UTC")


class DevelopmentConfig(Config):
    DEBUG: bool = True


class TestingConfig(Config):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE: bool = True
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "connect_args": {"timeout": 20},
        "pool_pre_ping": True,
        "pool_size": 10,
        "pool_recycle": 1800,
    }
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "").split(",")
        if o.strip()
    ]


_config_map: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config() -> type[Config]:
    env = os.environ.get("FLASK_ENV", "development")
    return _config_map.get(env, DevelopmentConfig)
