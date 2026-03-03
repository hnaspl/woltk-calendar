"""Admin API: user management and system settings (admin only)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import auth_service
from app.extensions import db
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.utils.permissions import has_permission
from app.i18n import _t

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_permission(perm_code: str):
    """Return an error tuple if the current user lacks the permission, else None."""
    if not has_permission(None, perm_code):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    return None


@bp.get("/users")
@login_required
def list_users():
    err = _require_permission("list_system_users")
    if err:
        return err
    users = auth_service.list_all_users()
    return jsonify([u.to_dict() for u in users]), 200


@bp.get("/dashboard")
@login_required
def dashboard_stats():
    err = _require_permission("list_system_users")
    if err:
        return err

    import os
    from datetime import datetime, timezone
    import sqlalchemy as sa
    from app.models.user import User
    from app.models.guild import Guild
    from app.models.raid import RaidEvent
    from app.models.character import Character
    from app.models.signup import Signup
    from app.models.notification import JobQueue
    from app.enums import JobStatus

    now = datetime.now(timezone.utc)

    total_users = db.session.scalar(sa.select(sa.func.count()).select_from(User))
    active_users = db.session.scalar(
        sa.select(sa.func.count()).select_from(User).where(User.is_active.is_(True))
    )
    admin_users = db.session.scalar(
        sa.select(sa.func.count()).select_from(User).where(User.is_admin.is_(True))
    )
    total_guilds = db.session.scalar(sa.select(sa.func.count()).select_from(Guild))
    total_raids = db.session.scalar(sa.select(sa.func.count()).select_from(RaidEvent))
    upcoming_raids = db.session.scalar(
        sa.select(sa.func.count()).select_from(RaidEvent).where(
            RaidEvent.starts_at_utc > now,
            RaidEvent.status != "cancelled",
        )
    )
    total_characters = db.session.scalar(sa.select(sa.func.count()).select_from(Character))
    total_signups = db.session.scalar(sa.select(sa.func.count()).select_from(Signup))
    pending_jobs = db.session.scalar(
        sa.select(sa.func.count()).select_from(JobQueue).where(
            JobQueue.status == JobStatus.QUEUED.value
        )
    )
    failed_jobs = db.session.scalar(
        sa.select(sa.func.count()).select_from(JobQueue).where(
            JobQueue.status == JobStatus.FAILED.value
        )
    )

    from flask import current_app
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_path = db_uri.replace("sqlite:///", "") if db_uri.startswith("sqlite:///") else None
    try:
        database_size_kb = round(os.path.getsize(db_path) / 1024, 1) if db_path else None
    except OSError:
        database_size_kb = None

    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "total_guilds": total_guilds,
        "total_raids": total_raids,
        "upcoming_raids": upcoming_raids,
        "total_characters": total_characters,
        "total_signups": total_signups,
        "pending_jobs": pending_jobs,
        "failed_jobs": failed_jobs,
        "database_size_kb": database_size_kb,
    }), 200


@bp.put("/users/<int:user_id>")
@login_required
def update_user(user_id: int):
    err = _require_permission("manage_system_users")
    if err:
        return err
    user = auth_service.get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": _t("api.admin.userNotFound")}), 404
    if user.id == current_user.id:
        return jsonify({"error": _t("api.admin.cannotModifySelf")}), 400

    # Protect the primary site admin (user ID 1) from being modified
    if user.id == 1:
        return jsonify({"error": _t("api.admin.cannotModifyPrimary")}), 403

    data = get_json()

    if "is_active" in data:
        user = auth_service.set_user_active(user, bool(data["is_active"]))

    if "is_admin" in data:
        user = auth_service.set_user_admin(user, bool(data["is_admin"]))

    return jsonify(user.to_dict()), 200


@bp.delete("/users/<int:user_id>")
@login_required
def delete_user(user_id: int):
    err = _require_permission("manage_system_users")
    if err:
        return err
    user = auth_service.get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": _t("api.admin.userNotFound")}), 404
    if user.id == current_user.id:
        return jsonify({"error": _t("api.admin.cannotDeleteSelf")}), 400

    # Protect the primary site admin (user ID 1) from being deleted
    if user.id == 1:
        return jsonify({"error": _t("api.admin.cannotDeletePrimary")}), 403

    auth_service.delete_user(user)
    return jsonify({"message": _t("api.admin.userDeleted")}), 200


@bp.post("/sync-characters")
@login_required
def trigger_sync():
    """Manually trigger a sync of all characters."""
    err = _require_permission("trigger_sync")
    if err:
        return err
    from app.jobs.handlers import handle_sync_all_characters
    handle_sync_all_characters({})
    return jsonify({"message": _t("api.admin.syncCompleted")}), 200


# ---------------------------------------------------------------------------
# Global system settings
# ---------------------------------------------------------------------------

@bp.get("/settings/system")
@login_required
def get_system_settings():
    """Return all global system settings. Any logged-in user can read."""
    return _system_settings_response()


def _system_settings_response():
    """Build the system settings JSON response from the database."""
    from app.models.system_setting import SystemSetting
    rows = db.session.execute(db.select(SystemSetting)).scalars().all()
    settings = {r.key: r.value for r in rows}
    return jsonify(settings), 200


@bp.put("/settings/system")
@login_required
def update_system_settings():
    """Update global system settings. Requires manage_system_settings permission."""
    err = _require_permission("manage_system_settings")
    if err:
        return err
    from app.models.system_setting import SystemSetting
    data = get_json()
    # Boolean settings — validate and store as "true"/"false"
    bool_keys = {"wowhead_tooltips", "autosync_enabled"}
    for key in bool_keys:
        if key in data:
            val = "true" if data[key] in (True, "true", "1", 1) else "false"
            existing = db.session.get(SystemSetting, key)
            if existing:
                existing.value = val
            else:
                db.session.add(SystemSetting(key=key, value=val))
    # Integer settings
    int_keys = {"autosync_interval_minutes"}
    for key in int_keys:
        if key in data:
            try:
                val = str(max(5, int(data[key])))
            except (ValueError, TypeError):
                return jsonify({"error": _t("api.admin.invalidInteger", key=key)}), 400
            existing = db.session.get(SystemSetting, key)
            if existing:
                existing.value = val
            else:
                db.session.add(SystemSetting(key=key, value=val))
    db.session.commit()

    # Reschedule auto-sync if autosync settings were changed
    if "autosync_enabled" in data or "autosync_interval_minutes" in data:
        from app.jobs.scheduler import _apply_autosync_schedule, get_autosync_config
        _apply_autosync_schedule(get_autosync_config())

    return _system_settings_response()


# ---------------------------------------------------------------------------
# Discord OAuth configuration
# ---------------------------------------------------------------------------

@bp.get("/settings/discord")
@login_required
def get_discord_settings():
    """Return Discord OAuth settings (client_secret is masked). Global admin only.

    Includes ``callback_url``: the exact URL the admin must register in the
    Discord Developer Portal under *Redirects*.  It is auto-generated from
    the current request so the admin cannot mis-type the path.
    """
    if not current_user.is_admin:
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    from flask import request
    from app.models.system_setting import SystemSetting
    keys = ["discord_client_id", "discord_client_secret"]
    rows = db.session.execute(
        db.select(SystemSetting).where(SystemSetting.key.in_(keys))
    ).scalars().all()
    settings = {r.key: r.value for r in rows}

    # Mask the client secret for display
    secret = settings.get("discord_client_secret", "")
    if secret:
        settings["discord_client_secret"] = "••••••••"

    # Auto-generated callback URL – this is what goes into Discord "Redirects"
    from app.services.discord_service import DISCORD_CALLBACK_PATH
    settings["callback_url"] = f"{request.scheme}://{request.host}{DISCORD_CALLBACK_PATH}"

    return jsonify(settings), 200


@bp.put("/settings/discord")
@login_required
def update_discord_settings():
    """Update Discord OAuth settings. Client secret is encrypted before storage. Global admin only."""
    if not current_user.is_admin:
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    from app.models.system_setting import SystemSetting
    from app.utils.encryption import encrypt_value

    data = get_json()
    allowed_keys = {"discord_client_id"}
    for key in allowed_keys:
        if key in data:
            val = str(data[key]).strip()
            existing = db.session.get(SystemSetting, key)
            if existing:
                existing.value = val
            else:
                db.session.add(SystemSetting(key=key, value=val))

    # Encrypt the client secret before storing
    if "discord_client_secret" in data:
        raw_secret = str(data["discord_client_secret"]).strip()
        # Skip if placeholder (masked value from frontend)
        if raw_secret and raw_secret != "••••••••":
            encrypted = encrypt_value(raw_secret)
            existing = db.session.get(SystemSetting, "discord_client_secret")
            if existing:
                existing.value = encrypted
            else:
                db.session.add(SystemSetting(key="discord_client_secret", value=encrypted))

    db.session.commit()
    return jsonify({"message": _t("api.admin.discordSettingsSaved")}), 200
