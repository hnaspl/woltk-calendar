"""Internationalization support — unified translations for backend and frontend.

Loads translation JSON files from the ``translations/`` directory.
The same JSON files are used by both the Flask backend (via this module)
and the Vue frontend (via vue-i18n).

Usage in API routes::

    from app.i18n import _t

    return jsonify({"error": _t("common.errors.forbidden")}), 403

The locale is determined per-request from ``current_user.language`` or the
``Accept-Language`` header.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from flask import has_request_context, request

_TRANSLATIONS: dict[str, dict] = {}
_SUPPORTED_LOCALES = ("en", "pl")
_DEFAULT_LOCALE = "en"
_TRANSLATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "translations",
)


def _load_translations() -> None:
    """Load all locale JSON files into memory (called once at startup)."""
    global _TRANSLATIONS
    for locale in _SUPPORTED_LOCALES:
        path = os.path.join(_TRANSLATIONS_DIR, f"{locale}.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                _TRANSLATIONS[locale] = json.load(f)


def _get_locale() -> str:
    """Determine the locale for the current request."""
    # 1. Authenticated user's preference
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            lang = getattr(current_user, "language", None)
            if lang and lang in _SUPPORTED_LOCALES:
                return lang
    except Exception:
        pass

    # 2. Accept-Language header
    if has_request_context():
        best = request.accept_languages.best_match(_SUPPORTED_LOCALES, default=_DEFAULT_LOCALE)
        return best

    return _DEFAULT_LOCALE


def _resolve(data: dict, key: str) -> Optional[str]:
    """Resolve a dotted key path like 'common.errors.forbidden' from a dict."""
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current if isinstance(current, str) else None


def _t(key: str, **kwargs) -> str:
    """Translate a dotted key to the current locale, with optional interpolation.

    Placeholders use ``{name}`` syntax::

        _t("api.events.missingFields", fields="title, start_time")
        # → "Missing fields: title, start_time"

    Falls back to English, then to the raw key.
    """
    if not _TRANSLATIONS:
        _load_translations()

    locale = _get_locale()
    # Try requested locale
    result = _resolve(_TRANSLATIONS.get(locale, {}), key)
    # Fallback to English
    if result is None and locale != _DEFAULT_LOCALE:
        result = _resolve(_TRANSLATIONS.get(_DEFAULT_LOCALE, {}), key)
    # Fallback to raw key
    if result is None:
        return key

    # Interpolate {name} placeholders
    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, IndexError):
            pass  # Return unformatted if placeholders don't match

    return result


def get_supported_locales() -> tuple:
    """Return the tuple of supported locale codes."""
    return _SUPPORTED_LOCALES


def init_i18n(app) -> None:
    """Initialize i18n by loading translations (call from app factory)."""
    _load_translations()
    app.config["SUPPORTED_LOCALES"] = _SUPPORTED_LOCALES
    app.config["DEFAULT_LOCALE"] = _DEFAULT_LOCALE
