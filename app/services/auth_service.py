"""Auth service: user registration, lookup, and management."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import bcrypt, db
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.models.system_setting import SystemSetting
from app.i18n import _t


def _get_setting(key: str, default: str = "") -> str:
    """Read a single system setting from the DB."""
    row = db.session.get(SystemSetting, key)
    return row.value if row else default


def is_email_activation_required() -> bool:
    """Return True if email activation is enabled in system settings."""
    return _get_setting("email_activation_required", "false") == "true"


def get_password_policy() -> dict:
    """Return password policy from system settings."""
    return {
        "min_length": int(_get_setting("password_min_length", "8")),
        "require_uppercase": _get_setting("password_require_uppercase", "false") == "true",
        "require_lowercase": _get_setting("password_require_lowercase", "false") == "true",
        "require_digit": _get_setting("password_require_digit", "false") == "true",
        "require_special": _get_setting("password_require_special", "false") == "true",
    }


def validate_password_policy(password: str) -> Optional[str]:
    """Validate a password against the configured policy.

    Returns an error i18n key if validation fails, None if OK.
    """
    policy = get_password_policy()

    if len(password) < policy["min_length"]:
        return "auth.errors.passwordTooShort"

    if policy["require_uppercase"] and not any(c.isupper() for c in password):
        return "auth.errors.passwordNeedsUppercase"

    if policy["require_lowercase"] and not any(c.islower() for c in password):
        return "auth.errors.passwordNeedsLowercase"

    if policy["require_digit"] and not any(c.isdigit() for c in password):
        return "auth.errors.passwordNeedsDigit"

    if policy["require_special"] and not any(not c.isalnum() for c in password):
        return "auth.errors.passwordNeedsSpecial"

    return None


def register_user(
    email: str,
    username: str,
    password: str,
    display_name: Optional[str] = None,
    create_tenant: bool = True,
) -> User:
    """Create a new user and optionally provision a tenant workspace.

    Raises ValueError on duplicate email/username.
    """
    existing_email = db.session.execute(
        sa.select(User).where(User.email == email)
    ).scalar_one_or_none()
    if existing_email:
        raise ValueError(_t("auth.errors.emailTaken"))

    existing_username = db.session.execute(
        sa.select(User).where(User.username == username)
    ).scalar_one_or_none()
    if existing_username:
        raise ValueError(_t("auth.errors.usernameTaken"))

    activation_required = is_email_activation_required()
    activation_token = None
    activation_expires = None
    if activation_required:
        activation_token = secrets.token_urlsafe(64)
        activation_expires = datetime.now(timezone.utc) + timedelta(days=3)

    user = User(
        email=email,
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        display_name=display_name or username,
        email_verified=not activation_required,
        activation_token=activation_token,
        activation_token_expires_at=activation_expires,
    )
    db.session.add(user)
    db.session.flush()  # get user.id before creating tenant

    if create_tenant:
        # Auto-create tenant workspace for the new user
        from app.services import tenant_service
        tenant_service.create_tenant(owner=user)
    else:
        # No tenant — just commit the user
        db.session.commit()

    return user


def activate_user(token: str) -> Optional[User]:
    """Activate a user account via activation token.

    Returns the user on success, None if token is invalid/expired.
    """
    user = db.session.execute(
        sa.select(User).where(User.activation_token == token)
    ).scalar_one_or_none()

    if not user:
        return None

    if user.activation_token_expires_at and datetime.now(timezone.utc) > user.activation_token_expires_at:
        return None

    user.email_verified = True
    user.activation_token = None
    user.activation_token_expires_at = None
    db.session.commit()
    return user


def create_password_reset_token(user: User) -> str:
    """Generate a password reset token for the given user.

    Invalidates any existing unused tokens for the user.
    Returns the raw token string.
    """
    # Invalidate existing tokens
    db.session.execute(
        sa.update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=datetime.now(timezone.utc))
    )

    token_str = secrets.token_urlsafe(64)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token_str,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.session.add(reset_token)
    db.session.commit()
    return token_str


def reset_password_with_token(token: str, new_password: str) -> Optional[User]:
    """Reset a user's password using a valid reset token.

    Returns the user on success, None if token is invalid/expired/used.
    """
    reset_token = db.session.execute(
        sa.select(PasswordResetToken).where(PasswordResetToken.token == token)
    ).scalar_one_or_none()

    if not reset_token or not reset_token.is_valid():
        return None

    user = reset_token.user
    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    reset_token.used_at = datetime.now(timezone.utc)
    db.session.commit()
    return user


def cleanup_unactivated_accounts() -> int:
    """Remove user accounts that have not been activated within 3 days.

    Returns the count of deleted accounts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    users = db.session.execute(
        sa.select(User).where(
            User.email_verified.is_(False),
            User.activation_token.isnot(None),
            User.created_at < cutoff,
            User.auth_provider == "local",
        )
    ).scalars().all()

    count = 0
    for user in users:
        # Delete associated tenant if user owns one
        from app.models.tenant import Tenant
        tenant = db.session.execute(
            sa.select(Tenant).where(Tenant.owner_id == user.id)
        ).scalar_one_or_none()
        if tenant:
            db.session.delete(tenant)
        db.session.delete(user)
        count += 1

    if count:
        db.session.commit()
    return count


def verify_password(user: User, password: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    return bcrypt.check_password_hash(user.password_hash, password)


def change_password(user: User, new_password: str) -> None:
    """Update the user's password hash."""
    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()


def update_profile(user: User, data: dict) -> User:
    """Update user profile fields."""
    allowed = {"display_name", "timezone", "language"}
    for key, value in data.items():
        if key in allowed and value is not None:
            # Enforce length limits matching database column sizes
            if key == "display_name" and len(str(value)) > 100:
                continue
            if key == "timezone" and len(str(value)) > 64:
                continue
            if key == "language" and len(str(value)) > 5:
                continue
            setattr(user, key, value)
    db.session.commit()
    return user


def get_user_by_email(email: str) -> Optional[User]:
    return db.session.execute(
        sa.select(User).where(User.email == email)
    ).scalar_one_or_none()


def get_user_by_id(user_id: int) -> Optional[User]:
    return db.session.get(User, user_id)


def list_all_users() -> list[User]:
    """Return all users (admin only)."""
    return list(db.session.execute(
        sa.select(User).order_by(User.created_at.desc())
    ).scalars().all())


def set_user_active(user: User, active: bool) -> User:
    """Enable or disable a user account."""
    user.is_active = active
    db.session.commit()
    return user


def set_user_admin(user: User, admin: bool) -> User:
    """Promote or revoke global admin status for a user."""
    user.is_admin = admin
    db.session.commit()
    return user


def delete_user(user: User) -> None:
    """Permanently delete a user."""
    db.session.delete(user)
    db.session.commit()
