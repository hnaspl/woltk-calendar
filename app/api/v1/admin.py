"""Admin API: user management and system settings (admin only)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import auth_service
from app.extensions import db
from app.utils.auth import login_required
from app.utils.permissions import has_permission

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_permission(perm_code: str):
    """Return an error tuple if the current user lacks the permission, else None."""
    if not has_permission(None, perm_code):
        return jsonify({"error": f"Permission '{perm_code}' required"}), 403
    return None


@bp.get("/users")
@login_required
def list_users():
    err = _require_permission("list_system_users")
    if err:
        return err
    users = auth_service.list_all_users()
    return jsonify([u.to_dict() for u in users]), 200


@bp.put("/users/<int:user_id>")
@login_required
def update_user(user_id: int):
    err = _require_permission("manage_system_users")
    if err:
        return err
    user = auth_service.get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if user.id == current_user.id:
        return jsonify({"error": "Cannot modify your own account here"}), 400

    # Protect the primary site admin (user ID 1) from being modified
    if user.id == 1:
        return jsonify({"error": "Cannot modify the primary site admin"}), 403

    data = request.get_json(silent=True) or {}

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
        return jsonify({"error": "User not found"}), 404
    if user.id == current_user.id:
        return jsonify({"error": "Cannot delete your own account"}), 400

    # Protect the primary site admin (user ID 1) from being deleted
    if user.id == 1:
        return jsonify({"error": "Cannot delete the primary site admin"}), 403

    auth_service.delete_user(user)
    return jsonify({"message": "User deleted"}), 200


# ---------------------------------------------------------------------------
# Auto-sync settings
# ---------------------------------------------------------------------------

@bp.get("/settings/autosync")
@login_required
def get_autosync_settings():
    """Return current auto-sync settings."""
    err = _require_permission("manage_autosync")
    if err:
        return err
    from app.jobs.scheduler import get_autosync_config
    return jsonify(get_autosync_config()), 200


@bp.put("/settings/autosync")
@login_required
def update_autosync_settings():
    """Update auto-sync settings and reschedule the job."""
    err = _require_permission("manage_autosync")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    from app.jobs.scheduler import update_autosync_config
    config = update_autosync_config(data)
    return jsonify(config), 200


@bp.post("/sync-characters")
@login_required
def trigger_sync():
    """Manually trigger a sync of all characters."""
    err = _require_permission("trigger_sync")
    if err:
        return err
    from app.jobs.handlers import handle_sync_all_characters
    handle_sync_all_characters({})
    return jsonify({"message": "Sync completed"}), 200


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
    data = request.get_json(silent=True) or {}
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
            val = str(max(5, int(data[key])))
            existing = db.session.get(SystemSetting, key)
            if existing:
                existing.value = val
            else:
                db.session.add(SystemSetting(key=key, value=val))
    db.session.commit()
    return _system_settings_response()
