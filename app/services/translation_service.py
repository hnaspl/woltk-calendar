"""Translation management service.

Provides CRUD operations for translation overrides and tools for detecting
missing translations between locales.  All overrides are stored in the
database (TranslationOverride model) and merged on top of the static JSON
files at read time — the JSON files on disk are never modified.

Security:
    - Only global admins can create/update/delete overrides (enforced at API layer)
    - Values are sanitized via the shared ``app.utils.sanitizer`` module: no HTML
      tags, no script injection, no shell commands, no unknown placeholders
    - Key format is validated to prevent path traversal or injection
    - Maximum value length is enforced (10,000 characters)
    - All mutations are audit-logged with the admin user ID
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import sqlalchemy as sa

from app.extensions import db
from app.models.translation_override import TranslationOverride
from app.utils.sanitizer import (
    sanitize_translation,
    validate_translation_key,
    get_allowed_translation_variables,
    MAX_TRANSLATION_LENGTH,
    TRANSLATION_VARIABLE_EXAMPLES,
)

logger = logging.getLogger(__name__)

_TRANSLATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "translations",
)
_SUPPORTED_LOCALES = ("en", "pl")

# Re-export for API layer
MAX_VALUE_LENGTH = MAX_TRANSLATION_LENGTH


# ── Helpers ──────────────────────────────────────────────────────────────


def _load_file_translations(locale: str) -> dict:
    """Load static JSON translations for a locale."""
    path = os.path.join(_TRANSLATIONS_DIR, f"{locale}.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    """Flatten a nested dict into dotted-key → value pairs."""
    result: dict[str, str] = {}
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_flatten(v, full_key))
        else:
            result[full_key] = str(v) if v is not None else ""
    return result


def _unflatten(flat: dict[str, str]) -> dict:
    """Convert dotted-key pairs back into a nested dict."""
    result: dict = {}
    for dotted_key, value in sorted(flat.items()):
        parts = dotted_key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def _get_top_level_sections(flat_keys: set[str]) -> list[str]:
    """Extract sorted unique top-level sections from flat keys."""
    sections = set()
    for key in flat_keys:
        parts = key.split(".", 1)
        sections.add(parts[0])
    return sorted(sections)


# ── Public API ───────────────────────────────────────────────────────────


def get_allowed_variables() -> list[str]:
    """Return sorted list of allowed placeholder variables for documentation."""
    return get_allowed_translation_variables()


def get_supported_locales() -> list[str]:
    """Return list of supported locale codes."""
    return list(_SUPPORTED_LOCALES)


def get_translations_flat(locale: str) -> dict[str, str]:
    """Return flat (dotted-key) translations for a locale, with DB overrides merged."""
    if locale not in _SUPPORTED_LOCALES:
        return {}

    file_data = _load_file_translations(locale)
    flat = _flatten(file_data)

    # Merge DB overrides
    overrides = TranslationOverride.query.filter_by(locale=locale).all()
    for override in overrides:
        flat[override.key] = override.value

    return flat


def get_translations_nested(locale: str) -> dict:
    """Return nested translations for a locale, with DB overrides merged."""
    flat = get_translations_flat(locale)
    return _unflatten(flat)


def get_sections(locale: str) -> list[str]:
    """Return sorted list of top-level translation sections for a locale."""
    flat = get_translations_flat(locale)
    return _get_top_level_sections(set(flat.keys()))


def get_section_translations(locale: str, section: str) -> dict[str, str]:
    """Return flat translations for a specific section (top-level key prefix)."""
    flat = get_translations_flat(locale)
    prefix = f"{section}."
    return {k: v for k, v in flat.items() if k.startswith(prefix) or k == section}


def get_missing_translations() -> dict[str, list[str]]:
    """Detect keys that exist in one locale but not in another."""
    all_flat: dict[str, set[str]] = {}
    for locale in _SUPPORTED_LOCALES:
        flat = get_translations_flat(locale)
        all_flat[locale] = set(flat.keys())

    result: dict[str, list[str]] = {}
    for locale in _SUPPORTED_LOCALES:
        other_keys = set()
        for other_locale in _SUPPORTED_LOCALES:
            if other_locale != locale:
                other_keys |= all_flat.get(other_locale, set())
        missing = sorted(other_keys - all_flat.get(locale, set()))
        if missing:
            result[f"missing_in_{locale}"] = missing

    return result


def get_overrides(locale: str | None = None) -> list[dict]:
    """List all translation overrides, optionally filtered by locale."""
    query = TranslationOverride.query
    if locale:
        query = query.filter_by(locale=locale)
    return [o.to_dict() for o in query.order_by(
        TranslationOverride.locale, TranslationOverride.key
    ).all()]


def set_override(locale: str, key: str, value: str, user_id: int | None = None) -> TranslationOverride:
    """Create or update a translation override.

    Raises :class:`ValueError` if the key format is invalid, the value
    contains dangerous content, or an unknown placeholder is used.
    """
    if locale not in _SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported locale: {locale}")

    key_error = validate_translation_key(key)
    if key_error:
        raise ValueError(key_error)

    sanitized, value_error = sanitize_translation(value)
    if value_error:
        raise ValueError(value_error)

    override = TranslationOverride.query.filter_by(locale=locale, key=key).first()
    if override:
        override.value = sanitized
        override.updated_by = user_id
        logger.info("Translation override updated: %s:%s by user %s", locale, key, user_id)
    else:
        override = TranslationOverride(
            locale=locale, key=key, value=sanitized, updated_by=user_id,
        )
        db.session.add(override)
        logger.info("Translation override created: %s:%s by user %s", locale, key, user_id)

    db.session.commit()
    return override


def set_overrides_bulk(locale: str, translations: dict[str, str], user_id: int | None = None) -> int:
    """Bulk create/update translation overrides. Returns count of changes.

    Silently skips entries with invalid keys or dangerous values.
    """
    if locale not in _SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported locale: {locale}")

    count = 0
    for key, value in translations.items():
        if validate_translation_key(key) is not None:
            continue
        sanitized, err = sanitize_translation(str(value))
        if err is not None:
            continue

        override = TranslationOverride.query.filter_by(locale=locale, key=key).first()
        if override:
            if override.value != sanitized:
                override.value = sanitized
                override.updated_by = user_id
                count += 1
        else:
            override = TranslationOverride(
                locale=locale, key=key, value=sanitized, updated_by=user_id
            )
            db.session.add(override)
            count += 1

    if count > 0:
        db.session.commit()
        logger.info("Bulk translation update: %d changes for %s by user %s", count, locale, user_id)

    return count


def delete_override(locale: str, key: str) -> bool:
    """Delete a translation override (reverts to file default). Returns True if found."""
    override = TranslationOverride.query.filter_by(locale=locale, key=key).first()
    if override:
        db.session.delete(override)
        db.session.commit()
        logger.info("Translation override deleted: %s:%s", locale, key)
        return True
    return False


def get_stats() -> dict[str, Any]:
    """Return translation statistics."""
    stats: dict[str, Any] = {"locales": {}}
    all_flat: dict[str, dict[str, str]] = {}

    for locale in _SUPPORTED_LOCALES:
        flat = get_translations_flat(locale)
        all_flat[locale] = flat
        override_count = TranslationOverride.query.filter_by(locale=locale).count()
        stats["locales"][locale] = {
            "total_keys": len(flat),
            "override_count": override_count,
            "sections": _get_top_level_sections(set(flat.keys())),
        }

    missing = get_missing_translations()
    stats["missing"] = missing
    stats["total_missing"] = sum(len(v) for v in missing.values())

    return stats
