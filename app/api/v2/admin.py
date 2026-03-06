"""Admin API: user management and system settings (admin only)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import auth_service
from app.extensions import db
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, require_system_permission
from app.i18n import _t

bp = Blueprint("admin", __name__, url_prefix="/admin")

MASKED_SECRET = "••••••••"


@bp.get("/users")
@login_required
def list_users():
    err = require_system_permission("list_system_users")
    if err:
        return err
    users = auth_service.list_all_users()
    return jsonify([u.to_dict() for u in users]), 200


@bp.get("/dashboard")
@login_required
def dashboard_stats():
    err = require_system_permission("list_system_users")
    if err:
        return err

    import os
    from datetime import datetime, timedelta, timezone
    import sqlalchemy as sa
    from app.models.user import User
    from app.models.guild import Guild, GuildMembership
    from app.models.raid import RaidEvent
    from app.models.character import Character
    from app.models.signup import Signup, LineupSlot
    from app.models.notification import JobQueue
    from app.models.tenant import Tenant, TenantMembership
    from app.enums import JobStatus

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)
    next_week_end = today_start + timedelta(days=14)

    # ── Core counts ──────────────────────────────────────────────
    total_users = db.session.scalar(sa.select(sa.func.count()).select_from(User))
    active_users = db.session.scalar(
        sa.select(sa.func.count()).select_from(User).where(User.is_active.is_(True))
    )
    admin_users = db.session.scalar(
        sa.select(sa.func.count()).select_from(User).where(User.is_admin.is_(True))
    )
    unverified_users = db.session.scalar(
        sa.select(sa.func.count()).select_from(User).where(
            User.email_verified.is_(False),
            User.activation_token.isnot(None),
        )
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

    # ── Growth metrics (7-day / 30-day) ──────────────────────────
    new_users_7d = db.session.scalar(
        sa.select(sa.func.count()).select_from(User).where(User.created_at >= week_ago)
    )
    new_users_30d = db.session.scalar(
        sa.select(sa.func.count()).select_from(User).where(User.created_at >= month_ago)
    )
    new_guilds_7d = db.session.scalar(
        sa.select(sa.func.count()).select_from(Guild).where(Guild.created_at >= week_ago)
    )
    new_events_7d = db.session.scalar(
        sa.select(sa.func.count()).select_from(RaidEvent).where(RaidEvent.created_at >= week_ago)
    )

    # ── Event pipeline ───────────────────────────────────────────
    events_today = db.session.scalar(
        sa.select(sa.func.count()).select_from(RaidEvent).where(
            RaidEvent.starts_at_utc >= today_start,
            RaidEvent.starts_at_utc < today_end,
            RaidEvent.status != "cancelled",
        )
    )
    events_this_week = db.session.scalar(
        sa.select(sa.func.count()).select_from(RaidEvent).where(
            RaidEvent.starts_at_utc >= today_start,
            RaidEvent.starts_at_utc < week_end,
            RaidEvent.status != "cancelled",
        )
    )
    events_next_week = db.session.scalar(
        sa.select(sa.func.count()).select_from(RaidEvent).where(
            RaidEvent.starts_at_utc >= week_end,
            RaidEvent.starts_at_utc < next_week_end,
            RaidEvent.status != "cancelled",
        )
    )
    completed_events = db.session.scalar(
        sa.select(sa.func.count()).select_from(RaidEvent).where(
            RaidEvent.status == "completed",
        )
    )
    cancelled_events = db.session.scalar(
        sa.select(sa.func.count()).select_from(RaidEvent).where(
            RaidEvent.status == "cancelled",
        )
    )

    # ── Signup statistics ────────────────────────────────────────
    avg_signups_per_event = None
    if total_raids and total_raids > 0:
        avg_signups_per_event = round(total_signups / total_raids, 1) if total_signups else 0

    bench_slots = db.session.scalar(
        sa.select(sa.func.count()).select_from(LineupSlot).where(
            LineupSlot.slot_group == "bench"
        )
    ) or 0

    # ── Job queue ────────────────────────────────────────────────
    pending_jobs = db.session.scalar(
        sa.select(sa.func.count()).select_from(JobQueue).where(
            JobQueue.status == JobStatus.QUEUED.value
        )
    )
    running_jobs = db.session.scalar(
        sa.select(sa.func.count()).select_from(JobQueue).where(
            JobQueue.status == JobStatus.RUNNING.value
        )
    )
    failed_jobs = db.session.scalar(
        sa.select(sa.func.count()).select_from(JobQueue).where(
            JobQueue.status == JobStatus.FAILED.value
        )
    )
    done_jobs = db.session.scalar(
        sa.select(sa.func.count()).select_from(JobQueue).where(
            JobQueue.status == JobStatus.DONE.value
        )
    )
    recent_queue = db.session.execute(
        sa.select(JobQueue).order_by(JobQueue.created_at.desc()).limit(10)
    ).scalars().all()

    # ── Database size ────────────────────────────────────────────
    from flask import current_app
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_path = db_uri.replace("sqlite:///", "") if db_uri.startswith("sqlite:///") else None
    try:
        database_size_kb = round(os.path.getsize(db_path) / 1024, 1) if db_path else None
    except OSError:
        database_size_kb = None

    # ── Tenant statistics ────────────────────────────────────────
    total_tenants = db.session.scalar(sa.select(sa.func.count()).select_from(Tenant))
    active_tenants = db.session.scalar(
        sa.select(sa.func.count()).select_from(Tenant).where(Tenant.is_active.is_(True))
    )
    suspended_tenants = db.session.scalar(
        sa.select(sa.func.count()).select_from(Tenant).where(Tenant.is_active.is_(False))
    )

    # Per-tenant breakdown (name, guilds count, members count, events count)
    tenants = db.session.execute(sa.select(Tenant).order_by(Tenant.created_at.desc())).scalars().all()
    tenant_breakdown = []
    for t in tenants:
        guild_count = db.session.scalar(
            sa.select(sa.func.count()).select_from(Guild).where(Guild.tenant_id == t.id)
        )
        member_count = db.session.scalar(
            sa.select(sa.func.count()).select_from(TenantMembership).where(
                TenantMembership.tenant_id == t.id
            )
        )
        # Count events across all guilds in this tenant
        tenant_guild_ids = db.session.execute(
            sa.select(Guild.id).where(Guild.tenant_id == t.id)
        ).scalars().all()
        event_count = 0
        if tenant_guild_ids:
            event_count = db.session.scalar(
                sa.select(sa.func.count()).select_from(RaidEvent).where(
                    RaidEvent.guild_id.in_(tenant_guild_ids)
                )
            ) or 0
        tenant_breakdown.append({
            "id": t.id,
            "name": t.name,
            "plan": t.plan or "free",
            "is_active": t.is_active,
            "guilds": guild_count or 0,
            "members": member_count or 0,
            "events": event_count,
        })

    # ── Recent registrations (last 10 users) ─────────────────────
    recent_users = db.session.execute(
        sa.select(User).order_by(User.created_at.desc()).limit(10)
    ).scalars().all()
    recent_registrations = [
        {"id": u.id, "username": u.username, "created_at": u.created_at.isoformat() + "Z" if u.created_at else None, "is_admin": u.is_admin}
        for u in recent_users
    ]

    # ── Recent events (next 10 upcoming) ─────────────────────────
    next_events = db.session.execute(
        sa.select(RaidEvent).where(
            RaidEvent.starts_at_utc >= now,
            RaidEvent.status != "cancelled",
        ).order_by(RaidEvent.starts_at_utc.asc()).limit(10)
    ).scalars().all()
    upcoming_event_list = []
    for ev in next_events:
        guild = db.session.get(Guild, ev.guild_id)
        signup_count = db.session.scalar(
            sa.select(sa.func.count()).select_from(Signup).where(Signup.raid_event_id == ev.id)
        )
        upcoming_event_list.append({
            "id": ev.id,
            "title": ev.title,
            "guild_name": guild.name if guild else "—",
            "starts_at": ev.starts_at_utc.isoformat() + "Z" if ev.starts_at_utc else None,
            "raid_size": ev.raid_size,
            "signups": signup_count or 0,
        })

    return jsonify({
        # Core counts
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "unverified_users": unverified_users,
        "total_guilds": total_guilds,
        "total_raids": total_raids,
        "upcoming_raids": upcoming_raids,
        "total_characters": total_characters,
        "total_signups": total_signups,
        # Growth
        "new_users_7d": new_users_7d,
        "new_users_30d": new_users_30d,
        "new_guilds_7d": new_guilds_7d,
        "new_events_7d": new_events_7d,
        # Event pipeline
        "events_today": events_today,
        "events_this_week": events_this_week,
        "events_next_week": events_next_week,
        "completed_events": completed_events,
        "cancelled_events": cancelled_events,
        # Signups
        "avg_signups_per_event": avg_signups_per_event,
        "bench_slots": bench_slots,
        # Jobs
        "pending_jobs": pending_jobs,
        "running_jobs": running_jobs,
        "failed_jobs": failed_jobs,
        "done_jobs": done_jobs,
        "recent_queue": [j.to_dict() for j in recent_queue],
        # System
        "database_size_kb": database_size_kb,
        # Tenants
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "suspended_tenants": suspended_tenants,
        "tenant_breakdown": tenant_breakdown,
        # Activity
        "recent_registrations": recent_registrations,
        "upcoming_event_list": upcoming_event_list,
    }), 200


@bp.put("/users/<int:user_id>")
@login_required
def update_user(user_id: int):
    err = require_system_permission("manage_system_users")
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
    err = require_system_permission("manage_system_users")
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
    err = require_system_permission("trigger_sync")
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
    # Mask sensitive values
    if settings.get("smtp_password"):
        settings["smtp_password"] = MASKED_SECRET
    return jsonify(settings), 200


@bp.put("/settings/system")
@login_required
def update_system_settings():
    """Update global system settings. Requires manage_system_settings permission."""
    err = require_system_permission("manage_system_settings")
    if err:
        return err
    from app.models.system_setting import SystemSetting
    data = get_json()
    # Boolean settings — validate and store as "true"/"false"
    bool_keys = {
        "wowhead_tooltips", "autosync_enabled",
        "email_activation_required",
        "password_require_uppercase", "password_require_lowercase",
        "password_require_digit", "password_require_special",
    }
    for key in bool_keys:
        if key in data:
            val = "true" if data[key] in (True, "true", "1", 1) else "false"
            existing = db.session.get(SystemSetting, key)
            if existing:
                existing.value = val
            else:
                db.session.add(SystemSetting(key=key, value=val))
    # Integer settings
    int_keys = {"autosync_interval_minutes": 5, "password_min_length": 4}
    for key, min_val in int_keys.items():
        if key in data:
            try:
                val = str(max(min_val, int(data[key])))
            except (ValueError, TypeError):
                return jsonify({"error": _t("api.admin.invalidInteger", key=key)}), 400
            existing = db.session.get(SystemSetting, key)
            if existing:
                existing.value = val
            else:
                db.session.add(SystemSetting(key=key, value=val))
    # String settings (SMTP config)
    str_keys = {"smtp_host", "smtp_username", "smtp_from_email", "smtp_from_name"}
    for key in str_keys:
        if key in data:
            val = str(data[key]).strip()
            existing = db.session.get(SystemSetting, key)
            if existing:
                existing.value = val
            else:
                db.session.add(SystemSetting(key=key, value=val))
    # SMTP port (integer with specific range)
    if "smtp_port" in data:
        try:
            port = max(1, min(65535, int(data["smtp_port"])))
            val = str(port)
        except (ValueError, TypeError):
            return jsonify({"error": _t("api.admin.invalidInteger", key="smtp_port")}), 400
        existing = db.session.get(SystemSetting, "smtp_port")
        if existing:
            existing.value = val
        else:
            db.session.add(SystemSetting(key="smtp_port", value=val))
    # SMTP TLS boolean
    if "smtp_tls" in data:
        val = "true" if data["smtp_tls"] in (True, "true", "1", 1) else "false"
        existing = db.session.get(SystemSetting, "smtp_tls")
        if existing:
            existing.value = val
        else:
            db.session.add(SystemSetting(key="smtp_tls", value=val))
    # SMTP password (sensitive — encrypt before storing)
    if "smtp_password" in data:
        raw = str(data["smtp_password"]).strip()
        if raw and raw != MASKED_SECRET:
            from app.utils.encryption import encrypt_value
            encrypted = encrypt_value(raw)
            existing = db.session.get(SystemSetting, "smtp_password")
            if existing:
                existing.value = encrypted
            else:
                db.session.add(SystemSetting(key="smtp_password", value=encrypted))
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
        settings["discord_client_secret"] = MASKED_SECRET

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
        if raw_secret and raw_secret != MASKED_SECRET:
            encrypted = encrypt_value(raw_secret)
            existing = db.session.get(SystemSetting, "discord_client_secret")
            if existing:
                existing.value = encrypted
            else:
                db.session.add(SystemSetting(key="discord_client_secret", value=encrypted))

    db.session.commit()
    return jsonify({"message": _t("api.admin.discordSettingsSaved")}), 200


# ---------------------------------------------------------------------------
# User guild-limit override
# ---------------------------------------------------------------------------

@bp.put("/users/<int:user_id>/guild-limit")
@login_required
def set_user_guild_limit(user_id: int):
    """Set max_guilds_override on a user. Requires manage_system_users permission."""
    err = require_system_permission("manage_system_users")
    if err:
        return err
    from app.models.user import User
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": _t("api.admin.userNotFound")}), 404
    data = get_json()
    value = data.get("max_guilds")
    if value is not None:
        try:
            value = int(value)
        except (ValueError, TypeError):
            return jsonify({"error": _t("api.admin.invalidInteger", key="max_guilds")}), 400
    user.max_guilds_override = value
    db.session.commit()
    return jsonify(user.to_dict()), 200


# ---------------------------------------------------------------------------
# Guild feature flags (admin)
# ---------------------------------------------------------------------------

@bp.get("/guilds/<int:guild_id>/features")
@login_required
def get_guild_features(guild_id: int):
    """Get feature flags for a guild. Requires manage_system_settings permission."""
    err = require_system_permission("manage_system_settings")
    if err:
        return err
    from app.services.feature_service import get_guild_features as _get_features
    return jsonify(_get_features(guild_id)), 200


@bp.put("/guilds/<int:guild_id>/features")
@login_required
def update_guild_features(guild_id: int):
    """Update feature flags for a guild. Requires manage_system_settings permission."""
    err = require_system_permission("manage_system_settings")
    if err:
        return err
    from app.services.feature_service import set_feature
    data = get_json()
    for key, enabled in data.items():
        set_feature(guild_id, str(key), bool(enabled))
    from app.services.feature_service import get_guild_features as _get_features
    return jsonify(_get_features(guild_id)), 200


# ---------------------------------------------------------------------------
# Platform features (global admin — enable/disable globally, paywall control)
# ---------------------------------------------------------------------------

@bp.get("/platform-features")
@login_required
def list_platform_features():
    """List all platform feature definitions with global enable/disable and paywall status."""
    err = require_system_permission("manage_system_settings")
    if err:
        return err
    from app.services.feature_service import list_platform_features as _list
    features = _list()
    return jsonify([f.to_dict() for f in features]), 200


@bp.put("/platform-features/<feature_key>")
@login_required
def update_platform_feature(feature_key: str):
    """Update a platform feature's global settings (enable/disable, paywall)."""
    err = require_system_permission("manage_system_settings")
    if err:
        return err
    from app.services.feature_service import set_platform_feature
    data = get_json()
    pf = set_platform_feature(
        feature_key,
        globally_enabled=data.get("globally_enabled"),
        requires_plan=data.get("requires_plan"),
        display_name=data.get("display_name"),
        description=data.get("description"),
    )
    return jsonify(pf.to_dict()), 200


# ---------------------------------------------------------------------------
# Tenant features (per-tenant feature control)
# ---------------------------------------------------------------------------

@bp.get("/tenants/<int:tenant_id>/features")
@login_required
def get_tenant_features(tenant_id: int):
    """Get feature flags for a tenant (merged with platform defaults)."""
    err = require_system_permission("manage_system_settings")
    if err:
        return err
    from app.services.feature_service import get_tenant_features as _get
    return jsonify(_get(tenant_id)), 200


@bp.put("/tenants/<int:tenant_id>/features")
@login_required
def update_tenant_features(tenant_id: int):
    """Update feature flags for a tenant."""
    err = require_system_permission("manage_system_settings")
    if err:
        return err
    from app.services.feature_service import set_tenant_feature, get_tenant_features as _get
    data = get_json()
    for key, enabled in data.items():
        set_tenant_feature(tenant_id, str(key), bool(enabled))
    return jsonify(_get(tenant_id)), 200
