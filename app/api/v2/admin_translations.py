"""Admin translation management API.

Provides endpoints for global admins to browse, edit, and manage translations
from the admin panel.  All changes are stored in the database as overrides —
the static JSON files on disk are never modified.

Security:
    - All write endpoints require global admin (``@require_admin``)
    - Values are sanitized at the service layer: no HTML, no scripts, no
      shell commands, no unknown placeholder variables
    - Keys must match ``^[a-zA-Z_][a-zA-Z0-9_]*(\\.[a-zA-Z_][a-zA-Z0-9_]*)*$``
    - Maximum value length: 10,000 characters
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.utils.auth import login_required
from app.utils.decorators import require_admin
from app.services import translation_service

logger = logging.getLogger(__name__)

bp = Blueprint("admin_translations", __name__)


@bp.get("/")
@login_required
@require_admin
def get_translation_stats():
    """Return translation statistics: counts, sections, missing keys."""
    stats = translation_service.get_stats()
    return jsonify(stats), 200


@bp.get("/locales")
@login_required
@require_admin
def get_locales():
    """Return list of supported locale codes."""
    return jsonify({"locales": translation_service.get_supported_locales()}), 200


@bp.get("/variables")
@login_required
@require_admin
def get_allowed_variables():
    """Return documentation on allowed placeholder variables.

    These are the only ``{variable}`` names permitted in translation values.
    Using any other placeholder will be rejected by the security filter.
    """
    from app.utils.sanitizer import TRANSLATION_VARIABLE_EXAMPLES
    variables = translation_service.get_allowed_variables()
    return jsonify({
        "allowed_variables": variables,
        "examples": TRANSLATION_VARIABLE_EXAMPLES,
        "usage": (
            "Use {variable_name} syntax in translation values. "
            "Only the listed variables are allowed. "
            "HTML tags, script injection, shell commands, and escape "
            "sequences are blocked. Emoji characters (🏰, ⚔️, etc.) "
            "are safe to use."
        ),
        "max_value_length": translation_service.MAX_VALUE_LENGTH,
        "key_format": "Dot-separated alphanumeric segments: admin.translations.saved",
    }), 200


@bp.get("/<locale>")
@login_required
@require_admin
def get_translations(locale: str):
    """Return all flat translations for a locale (with overrides merged)."""
    section = request.args.get("section")
    if section:
        flat = translation_service.get_section_translations(locale, section)
    else:
        flat = translation_service.get_translations_flat(locale)

    sections = translation_service.get_sections(locale)
    return jsonify({
        "locale": locale,
        "translations": flat,
        "sections": sections,
        "total": len(flat),
    }), 200


@bp.get("/<locale>/sections")
@login_required
@require_admin
def get_sections(locale: str):
    """Return list of top-level translation sections."""
    sections = translation_service.get_sections(locale)
    return jsonify({"locale": locale, "sections": sections}), 200


@bp.get("/missing")
@login_required
@require_admin
def get_missing():
    """Return keys missing from each locale."""
    missing = translation_service.get_missing_translations()
    return jsonify(missing), 200


@bp.get("/overrides")
@login_required
@require_admin
def get_overrides():
    """List all translation overrides."""
    locale = request.args.get("locale")
    overrides = translation_service.get_overrides(locale)
    return jsonify({"overrides": overrides, "total": len(overrides)}), 200


@bp.put("/<locale>")
@login_required
@require_admin
def update_translation(locale: str):
    """Update a single translation key.

    Request body: ``{"key": "admin.title", "value": "Admin Panel"}``

    Security: The value is validated against the security filter (no HTML,
    no scripts, no shell commands, only whitelisted placeholder variables).
    """
    data = request.get_json(silent=True) or {}
    key = data.get("key", "").strip()
    value = data.get("value", "")

    if not key:
        return jsonify({"error": "Translation key is required"}), 400
    if not isinstance(value, str):
        return jsonify({"error": "Value must be a string"}), 400

    try:
        override = translation_service.set_override(
            locale=locale,
            key=key,
            value=value,
            user_id=current_user.id,
        )
        logger.info(
            "Admin %s updated translation %s:%s",
            current_user.username, locale, key
        )
        return jsonify(override.to_dict()), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.put("/<locale>/bulk")
@login_required
@require_admin
def update_translations_bulk(locale: str):
    """Bulk update translations for a locale.

    Request body: ``{"translations": {"key1": "val1", "key2": "val2"}}``

    Entries with invalid keys or dangerous values are silently skipped.
    """
    data = request.get_json(silent=True) or {}
    translations = data.get("translations", {})

    if not isinstance(translations, dict):
        return jsonify({"error": "translations must be a dict of key→value pairs"}), 400

    try:
        count = translation_service.set_overrides_bulk(
            locale=locale,
            translations=translations,
            user_id=current_user.id,
        )
        logger.info(
            "Admin %s bulk-updated %d translations for %s",
            current_user.username, count, locale
        )
        return jsonify({"updated": count}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.delete("/<locale>/<path:key>")
@login_required
@require_admin
def delete_override(locale: str, key: str):
    """Delete a translation override (revert to file default)."""
    deleted = translation_service.delete_override(locale, key)
    if deleted:
        logger.info(
            "Admin %s deleted translation override %s:%s",
            current_user.username, locale, key
        )
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "Override not found"}), 404


@bp.get("/merged/<locale>")
@login_required
def get_merged_translations(locale: str):
    """Return full merged translations (file + overrides) for frontend consumption.

    This endpoint is available to any authenticated user so the frontend can
    fetch translations that include admin overrides.
    """
    nested = translation_service.get_translations_nested(locale)
    return jsonify(nested), 200
