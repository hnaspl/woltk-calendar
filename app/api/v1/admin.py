"""Admin API: user management and system settings (admin only)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import auth_service
from app.utils.auth import login_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_admin():
    """Return an error tuple if the current user is not an admin, else None."""
    if not current_user.is_admin:
        return jsonify({"error": "Admin privileges required"}), 403
    return None


@bp.get("/users")
@login_required
def list_users():
    err = _require_admin()
    if err:
        return err
    users = auth_service.list_all_users()
    return jsonify([u.to_dict() for u in users]), 200


@bp.put("/users/<int:user_id>")
@login_required
def update_user(user_id: int):
    err = _require_admin()
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

    return jsonify(user.to_dict()), 200


@bp.delete("/users/<int:user_id>")
@login_required
def delete_user(user_id: int):
    err = _require_admin()
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
    err = _require_admin()
    if err:
        return err
    from app.jobs.scheduler import get_autosync_config
    return jsonify(get_autosync_config()), 200


@bp.put("/settings/autosync")
@login_required
def update_autosync_settings():
    """Update auto-sync settings and reschedule the job."""
    err = _require_admin()
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
    err = _require_admin()
    if err:
        return err
    from app.jobs.handlers import handle_sync_all_characters
    handle_sync_all_characters({})
    return jsonify({"message": "Sync completed"}), 200
