"""Auth API: register, login, logout, me, profile, change-password, Discord OAuth."""

from __future__ import annotations

import secrets

from flask import Blueprint, current_app, jsonify, redirect, session
from flask_login import current_user, login_user, logout_user

from app.services import auth_service
from app.services import discord_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.utils.rate_limit import rate_limit
from app.utils.email_validator import validate_email
from app.i18n import _t

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/register")
@rate_limit(limit=5, window=60)
def register():
    data = get_json()
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    display_name = data.get("display_name")

    if not email or not username or not password:
        return jsonify({"error": _t("auth.errors.emailRequired")}), 400

    if len(email) > 255:
        return jsonify({"error": _t("auth.errors.emailTooLong")}), 400

    email_err = validate_email(
        email, check_mx=not current_app.config.get("TESTING", False),
    )
    if email_err:
        return jsonify({"error": _t(email_err)}), 400

    if len(username) < 2 or len(username) > 80:
        return jsonify({"error": _t("auth.errors.usernameLengthInvalid")}), 400

    if display_name is not None and len(display_name) > 100:
        return jsonify({"error": _t("auth.errors.displayNameTooLong")}), 400

    if len(password) < 8:
        return jsonify({"error": _t("auth.errors.passwordTooShort")}), 400

    try:
        user = auth_service.register_user(email, username, password, display_name)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    login_user(user, remember=True)
    return jsonify(user.to_dict()), 201


@bp.post("/login")
@rate_limit(limit=10, window=60)
def login():
    data = get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": _t("auth.errors.loginRequired")}), 400

    user = auth_service.get_user_by_email(email)
    if user is None:
        return jsonify({"error": _t("auth.errors.invalidCredentials")}), 401

    if getattr(user, "auth_provider", "local") != "local":
        return jsonify({"error": _t("auth.errors.useDiscordLogin")}), 400

    if not auth_service.verify_password(user, password):
        return jsonify({"error": _t("auth.errors.invalidCredentials")}), 401

    if not user.is_active:
        return jsonify({"error": _t("auth.errors.accountDisabled")}), 403

    login_user(user, remember=True)
    return jsonify(user.to_dict()), 200


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": _t("auth.messages.loggedOut")}), 200


@bp.get("/me")
@login_required
def me():
    return jsonify(current_user.to_dict()), 200


@bp.put("/profile")
@login_required
def update_profile():
    data = get_json()
    user = auth_service.update_profile(current_user, data)
    return jsonify(user.to_dict()), 200


@bp.post("/change-password")
@login_required
def change_password():
    data = get_json()
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password or not new_password:
        return jsonify({"error": _t("auth.errors.passwordRequired")}), 400

    if len(new_password) < 8:
        return jsonify({"error": _t("auth.errors.passwordTooShort")}), 400

    if not auth_service.verify_password(current_user, current_password):
        return jsonify({"error": _t("auth.errors.currentPasswordWrong")}), 400

    auth_service.change_password(current_user, new_password)
    return jsonify({"message": _t("auth.messages.passwordChanged")}), 200


# ---------------------------------------------------------------------------
# Discord OAuth2
# ---------------------------------------------------------------------------

@bp.get("/discord/enabled")
def discord_enabled():
    """Return whether Discord login is configured."""
    return jsonify({"enabled": discord_service.is_discord_enabled()}), 200


@bp.get("/discord/login")
def discord_login():
    """Redirect the user to Discord's authorization page."""
    state = secrets.token_urlsafe(32)
    session["discord_oauth_state"] = state
    url = discord_service.get_authorize_url(state)
    if not url:
        return jsonify({"error": _t("auth.errors.discordNotConfigured")}), 400
    return jsonify({"url": url}), 200


@bp.get("/discord/callback")
def discord_callback():
    """Handle the OAuth2 callback from Discord."""
    from flask import request

    try:
        code = request.args.get("code")
        state = request.args.get("state")

        if not code or not state:
            current_app.logger.warning("Discord callback missing code or state")
            return redirect("/login?error=discord_failed")

        expected_state = session.pop("discord_oauth_state", None)
        if state != expected_state:
            current_app.logger.warning("Discord callback state mismatch")
            return redirect("/login?error=discord_failed")

        discord_info = discord_service.exchange_code(code)
        if not discord_info:
            current_app.logger.warning("Discord code exchange failed")
            return redirect("/login?error=discord_failed")

        user = discord_service.get_or_create_discord_user(discord_info)
        if not user.is_active:
            current_app.logger.info("Discord user %s is disabled", user.username)
            return redirect("/login?error=account_disabled")

        login_user(user, remember=True)
        current_app.logger.info("Discord login successful for user %s", user.username)
        return redirect("/dashboard")
    except Exception:
        current_app.logger.exception("Unhandled error in Discord callback")
        return redirect("/login?error=discord_failed")
