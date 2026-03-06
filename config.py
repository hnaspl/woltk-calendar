"""Application configuration loaded from environment variables.

All session/cookie security settings are driven by FLASK_ENV:
  - "development" / "dev"  → HTTP-friendly (no Secure flag on cookies)
  - "production"           → HTTPS-enforced (Secure flag on cookies)

Only SECRET_KEY and FLASK_ENV are required to configure the app.
"""

from __future__ import annotations

import os
from datetime import timedelta


class Config:
    # ------------------------------------------------------------------ Flask
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG: bool = False
    TESTING: bool = False

    # --------------------------------------------------------------- Logging
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.environ.get("LOG_DIR", "")

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
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        seconds=int(os.environ.get("PERMANENT_SESSION_LIFETIME", "86400"))
    )

    # --------------------------------------------------------- Remember cookie
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_SAMESITE: str = "Lax"
    REMEMBER_COOKIE_SECURE: bool = False

    # ------------------------------------------------------------------ CORS
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    # ---------------------------------------------------------- Proxy Fix
    # Enable when running behind a reverse proxy (nginx, Vite dev-server,
    # Docker network, etc.) so Flask sees the real client IP via
    # X-Forwarded-For. Required for session_protection="strong".
    PROXY_FIX_ENABLED: bool = os.environ.get("PROXY_FIX_ENABLED", "true").lower() == "true"
    PROXY_FIX_NUM_PROXIES: int = int(os.environ.get("PROXY_FIX_NUM_PROXIES", "1"))

    # ----------------------------------------------------------- APScheduler
    SCHEDULER_ENABLED: bool = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
    SCHEDULER_TIMEZONE: str = os.environ.get("SCHEDULER_TIMEZONE", "UTC")

    # ------------------------------------------------ Tenant subdomain routing
    # Set APP_DOMAIN (e.g. "example.com") to enable tenant subdomain routing.
    # Requests to <slug>.example.com will auto-resolve the matching tenant.
    APP_DOMAIN: str = os.environ.get("APP_DOMAIN", "")


class DevelopmentConfig(Config):
    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False
    REMEMBER_COOKIE_SECURE: bool = False


class TestingConfig(Config):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True
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
    "dev": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config() -> type[Config]:
    env = os.environ.get("FLASK_ENV", "development")
    return _config_map.get(env, DevelopmentConfig)
