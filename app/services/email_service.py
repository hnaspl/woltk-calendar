"""Email service: SMTP-based email sending with dynamic config from system settings."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.system_setting import SystemSetting

logger = logging.getLogger(__name__)


def _get_setting(key: str, default: str = "") -> str:
    """Read a single system setting from the DB."""
    row = db.session.get(SystemSetting, key)
    return row.value if row else default


def get_smtp_config() -> dict:
    """Return the current SMTP configuration from system settings."""
    password = _get_setting("smtp_password")
    # Decrypt the password if it was encrypted
    if password:
        try:
            from app.utils.encryption import decrypt_value
            password = decrypt_value(password)
        except Exception:
            logger.debug("SMTP password decryption skipped (may be stored in plain text)")
    return {
        "host": _get_setting("smtp_host"),
        "port": int(_get_setting("smtp_port", "587")),
        "tls": _get_setting("smtp_tls", "true") == "true",
        "username": _get_setting("smtp_username"),
        "password": password,
        "from_email": _get_setting("smtp_from_email"),
        "from_name": _get_setting("smtp_from_name", "Raid Calendar"),
    }


def is_smtp_configured() -> bool:
    """Return True if SMTP settings are filled in."""
    cfg = get_smtp_config()
    return bool(cfg["host"] and cfg["from_email"])


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Send an email using the configured SMTP settings.

    Returns True on success, False on failure.
    """
    cfg = get_smtp_config()
    if not cfg["host"] or not cfg["from_email"]:
        logger.warning("SMTP not configured — cannot send email to %s", to_email)
        return False

    from_addr = cfg["from_email"]
    if cfg["from_name"]:
        from_addr = f"{cfg['from_name']} <{cfg['from_email']}>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg["tls"]:
            context = ssl.create_default_context()
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=15)
            server.starttls(context=context)
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=15)

        if cfg["username"] and cfg["password"]:
            server.login(cfg["username"], cfg["password"])

        server.sendmail(cfg["from_email"], to_email, msg.as_string())
        server.quit()
        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except (smtplib.SMTPException, OSError, TimeoutError):
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_activation_email(to_email: str, username: str, token: str, base_url: str) -> bool:
    """Send an account activation email."""
    activation_url = f"{base_url}/activate?token={token}"

    subject = "Activate your Raid Calendar account"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #1a1a2e; color: #e0e0e0; padding: 30px; border-radius: 8px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #f0c040; font-size: 24px; margin: 0;">Raid Calendar</h1>
        </div>
        <h2 style="color: #ffffff; font-size: 18px;">Welcome, {username}!</h2>
        <p style="line-height: 1.6;">Your account has been created. Please activate it by clicking the button below:</p>
        <div style="text-align: center; margin: 24px 0;">
            <a href="{activation_url}" style="display: inline-block; background: #f0c040; color: #1a1a2e; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 16px;">Activate Account</a>
        </div>
        <p style="line-height: 1.6; color: #aaa;">Or copy this link into your browser:</p>
        <p style="word-break: break-all; color: #f0c040; font-size: 13px;">{activation_url}</p>
        <hr style="border: none; border-top: 1px solid #333; margin: 24px 0;" />
        <p style="font-size: 12px; color: #888; line-height: 1.5;">
            <strong>Important:</strong> If you do not activate your account within 3 days, it will be automatically removed along with all associated data.
        </p>
        <p style="font-size: 12px; color: #666;">If you did not create this account, you can safely ignore this email.</p>
    </div>
    """

    text_body = (
        f"Welcome, {username}!\n\n"
        f"Activate your account: {activation_url}\n\n"
        "Important: If you do not activate within 3 days, your account will be removed.\n\n"
        "If you did not create this account, ignore this email."
    )

    return send_email(to_email, subject, html_body, text_body)


def send_password_reset_email(to_email: str, username: str, token: str, base_url: str) -> bool:
    """Send a password reset email."""
    reset_url = f"{base_url}/reset-password?token={token}"

    subject = "Reset your Raid Calendar password"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #1a1a2e; color: #e0e0e0; padding: 30px; border-radius: 8px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #f0c040; font-size: 24px; margin: 0;">Raid Calendar</h1>
        </div>
        <h2 style="color: #ffffff; font-size: 18px;">Password Reset</h2>
        <p style="line-height: 1.6;">Hi {username}, we received a request to reset your password. Click the button below to set a new password:</p>
        <div style="text-align: center; margin: 24px 0;">
            <a href="{reset_url}" style="display: inline-block; background: #f0c040; color: #1a1a2e; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 16px;">Reset Password</a>
        </div>
        <p style="line-height: 1.6; color: #aaa;">Or copy this link into your browser:</p>
        <p style="word-break: break-all; color: #f0c040; font-size: 13px;">{reset_url}</p>
        <hr style="border: none; border-top: 1px solid #333; margin: 24px 0;" />
        <p style="font-size: 12px; color: #888;">This link expires in 1 hour. If you did not request a password reset, ignore this email.</p>
    </div>
    """

    text_body = (
        f"Hi {username},\n\n"
        f"Reset your password: {reset_url}\n\n"
        "This link expires in 1 hour.\n"
        "If you did not request a password reset, ignore this email."
    )

    return send_email(to_email, subject, html_body, text_body)
