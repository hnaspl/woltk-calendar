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
    # Discord users have no password to change
    if getattr(current_user, "auth_provider", "local") != "local":
        return jsonify({"error": _t("auth.errors.useDiscordLogin")}), 400

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
    try:
        enabled = discord_service.is_discord_enabled()
    except Exception:
        current_app.logger.exception("Error checking Discord enabled status")
        enabled = False
    return jsonify({"enabled": enabled}), 200


@bp.get("/discord/login")
def discord_login():
    """Redirect the user to Discord's authorization page (HTTP 302).

    The redirect_uri is generated here and stored in the session so the
    callback handler can pass the *exact same* value to the token
    exchange — this prevents mismatches caused by proxy / header
    inconsistencies between the two requests.

    Uses ``prompt=none`` so users who have previously authorized the app
    skip the consent screen entirely.  If the user has *not* authorized
    before, Discord returns ``error=access_denied`` and the callback
    handler retries without ``prompt`` (which shows the consent dialog).
    """
    redirect_uri = discord_service.get_redirect_uri()
    if redirect_uri is None:
        current_app.logger.warning("Discord login: not configured")
        return redirect("/login?error=discord_not_configured")

    state = secrets.token_urlsafe(32)
    session["discord_oauth_state"] = state
    session["discord_redirect_uri"] = redirect_uri

    url = discord_service.get_authorize_url(
        state, redirect_uri=redirect_uri, prompt="none")
    if not url:
        current_app.logger.warning("Discord login: not configured")
        return redirect("/login?error=discord_not_configured")
    current_app.logger.info("Discord login: redirecting to Discord (redirect_uri=%s, prompt=none)",
                            redirect_uri)
    return redirect(url)


@bp.get("/discord/callback")
def discord_callback():
    """Handle the OAuth2 callback from Discord.

    Two expected flows:

    1. **Returning user** (``prompt=none`` succeeded):
       Discord redirects with ``code`` + ``state`` → exchange code, log in.

    2. **First-time user** (``prompt=none`` returned ``access_denied``):
       Discord redirects with ``error=access_denied`` + ``state`` →
       we verify the state, generate a *new* state, and redirect to
       Discord again **without** ``prompt`` so the consent dialog is
       shown.  Discord then completes the normal code flow.
    """
    from flask import request

    current_app.logger.info("Discord callback hit: %s", request.url)

    try:
        error_param = request.args.get("error")

        # ----- Handle prompt=none rejection (first-time users) -----
        if error_param == "access_denied":
            state = request.args.get("state")
            expected_state = session.pop("discord_oauth_state", None)
            stored_redirect_uri = session.get("discord_redirect_uri")

            if not state or state != expected_state:
                current_app.logger.warning(
                    "Discord access_denied callback with invalid state")
                return redirect("/login?error=discord_failed")

            # Re-issue a fresh state and redirect to Discord WITHOUT
            # prompt=none so the consent dialog is displayed.
            new_state = secrets.token_urlsafe(32)
            session["discord_oauth_state"] = new_state
            # Keep discord_redirect_uri in session for the real callback.

            redirect_uri = stored_redirect_uri or discord_service.get_redirect_uri()
            session["discord_redirect_uri"] = redirect_uri

            url = discord_service.get_authorize_url(
                new_state, redirect_uri=redirect_uri)
            if not url:
                return redirect("/login?error=discord_not_configured")
            current_app.logger.info(
                "Discord prompt=none denied (first-time user), "
                "retrying with consent dialog (redirect_uri=%s)",
                redirect_uri)
            return redirect(url)

        # ----- Normal code exchange flow -----
        code = request.args.get("code")
        state = request.args.get("state")

        if not code or not state:
            current_app.logger.warning("Discord callback missing code or state")
            return redirect("/login?error=discord_failed")

        expected_state = session.pop("discord_oauth_state", None)
        stored_redirect_uri = session.pop("discord_redirect_uri", None)

        if state != expected_state:
            current_app.logger.warning(
                "Discord callback state mismatch (expected=%s, got=%s)",
                "present" if expected_state else "missing",
                "present" if state else "missing",
            )
            return redirect("/login?error=discord_failed")

        # Use the stored redirect_uri so it matches the authorize URL exactly.
        # Falls back to auto-generation if session value was lost (best effort).
        if stored_redirect_uri:
            current_app.logger.info("Discord callback: using stored redirect_uri=%s",
                                    stored_redirect_uri)
        else:
            current_app.logger.warning(
                "Discord callback: stored redirect_uri missing from session, "
                "auto-generating (may cause mismatch)")

        current_app.logger.info("Discord callback: state verified, exchanging code")
        discord_info = discord_service.exchange_code(
            code, redirect_uri=stored_redirect_uri)
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
