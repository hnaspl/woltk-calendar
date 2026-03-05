"""v2 Guild Class-Role Matrix API.

Endpoints:
  GET    /api/v2/guilds/<guild_id>/class-role-matrix         — get resolved matrix
  PUT    /api/v2/guilds/<guild_id>/class-role-matrix/<class>  — set overrides for class
  DELETE /api/v2/guilds/<guild_id>/class-role-matrix/<class>  — reset class to defaults
  DELETE /api/v2/guilds/<guild_id>/class-role-matrix          — reset entire matrix
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.extensions import db
from app.i18n import _t
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, validate_required
from app.utils.decorators import require_guild_permission
from app.services import matrix_service
from app.services.matrix_service import VALID_ROLES

bp = Blueprint("guild_matrix", __name__)


@bp.get("/<int:guild_id>/class-role-matrix")
@login_required
@require_guild_permission()
def get_matrix(guild_id: int, membership):
    """Get the resolved class-role matrix for a guild."""
    matrix = matrix_service.resolve_matrix(guild_id)
    overrides = matrix_service.get_guild_overrides(guild_id)

    return jsonify({
        "guild_id": guild_id,
        "matrix": matrix,
        "defaults": matrix_service._get_guild_expansion_defaults(guild_id),
        "overrides": overrides,
        "has_overrides": bool(overrides),
    })


@bp.put("/<int:guild_id>/class-role-matrix/<class_name>")
@login_required
@require_guild_permission("manage_class_role_matrix")
def set_class_overrides(guild_id: int, class_name: str, membership):
    """Set allowed roles for a class in this guild."""
    data = get_json()
    err = validate_required(data, "roles")
    if err:
        return err

    roles = data["roles"]
    if not isinstance(roles, list) or not roles:
        return jsonify({"error": _t("api.matrix.rolesRequired")}), 400

    valid_roles = VALID_ROLES
    invalid = set(roles) - valid_roles
    if invalid:
        return jsonify({"error": _t("api.matrix.invalidRoles", roles=", ".join(invalid))}), 400

    try:
        matrix_service.set_guild_overrides(guild_id, class_name, roles)
        db.session.commit()
    except ValueError:
        return jsonify({"error": _t("api.matrix.unknownClass")}), 400

    return jsonify({
        "message": _t("api.matrix.classUpdated"),
        "class_name": class_name,
        "roles": roles,
    })


@bp.delete("/<int:guild_id>/class-role-matrix/<class_name>")
@login_required
@require_guild_permission("manage_class_role_matrix")
def reset_class(guild_id: int, class_name: str, membership):
    """Reset a class to expansion defaults (remove guild overrides)."""
    try:
        matrix_service.reset_guild_class(guild_id, class_name)
        db.session.commit()
    except ValueError:
        return jsonify({"error": _t("api.matrix.unknownClass")}), 400

    return jsonify({
        "message": _t("api.matrix.classReset"),
        "class_name": class_name,
    })


@bp.delete("/<int:guild_id>/class-role-matrix")
@login_required
@require_guild_permission("manage_class_role_matrix")
def reset_matrix(guild_id: int, membership):
    """Reset entire matrix to expansion defaults."""
    matrix_service.reset_guild_matrix(guild_id)
    db.session.commit()

    return jsonify({
        "message": _t("api.matrix.matrixReset"),
    })
