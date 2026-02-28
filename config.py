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
        "mysql+pymysql://{user}:{password}@{host}:{port}/{name}".format(
            user=os.environ.get("DB_USER", "user"),
            password=os.environ.get("DB_PASSWORD", "password"),
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "3306"),
            name=os.environ.get("DB_NAME", "wotlk_calendar"),
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # --------------------------------------------------------------- Session
    SESSION_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        seconds=int(os.environ.get("PERMANENT_SESSION_LIFETIME", "86400"))
    )

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
