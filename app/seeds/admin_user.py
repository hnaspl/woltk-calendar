"""Seed a default admin user into the database."""

from __future__ import annotations

import logging
import os
import secrets

import sqlalchemy as sa

from app.extensions import bcrypt, db
from app.models.user import User
from app.services import tenant_service

logger = logging.getLogger(__name__)


def seed_admin_user(
    email: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> bool:
    """Create the initial admin user if it does not already exist.

    Credentials fall back to environment variables:
      - ADMIN_EMAIL    (default: admin@wotlk-calendar.local)
      - ADMIN_USERNAME (default: admin)
      - ADMIN_PASSWORD (REQUIRED in production – a random password is
        generated and logged if not set)

    Returns True if a new user was inserted, False if it already existed.
    """
    email = (email or os.environ.get("ADMIN_EMAIL", "admin@wotlk-calendar.local")).strip().lower()
    username = (username or os.environ.get("ADMIN_USERNAME", "admin")).strip()
    password = password or os.environ.get("ADMIN_PASSWORD")

    # Check if admin already exists BEFORE generating a password to avoid
    # logging a random password that will never be used.
    existing = db.session.execute(
        sa.select(User).where((User.email == email) | (User.username == username))
    ).scalars().first()

    if existing is not None:
        return False

    if not password:
        password = secrets.token_urlsafe(16)
        logger.warning(
            "ADMIN_PASSWORD not set. Generated random admin password: %s  "
            "Set ADMIN_PASSWORD env var to use a fixed password.",
            password,
        )

    user = User(
        email=email,
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        display_name=username,
        is_active=True,
        is_admin=True,
    )
    db.session.add(user)
    db.session.commit()
    tenant_service.create_tenant(owner=user)
    logger.info("Created default tenant for admin user '%s'.", username)
    return True
