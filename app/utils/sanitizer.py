"""Shared input sanitization utilities.

Provides reusable functions for sanitizing user-provided text content
before it is stored in the database.  These utilities protect against:

- **HTML/script injection**: ``<script>``, ``<iframe>``, event handlers, etc.
- **Shell command injection**: ``$(cmd)``, backtick execution, pipe to shell
- **Encoding-based obfuscation**: hex escapes, unicode escapes, HTML entities
- **Placeholder abuse**: only whitelisted ``{variable}`` names are permitted
  when placeholder validation is enabled

Usage::

    from app.utils.sanitizer import sanitize_text, sanitize_translation

    # General text sanitization (descriptions, notes, instructions)
    clean, error = sanitize_text(user_input, max_length=5000)
    if error:
        return jsonify({"error": error}), 400

    # Translation-specific sanitization (validates {placeholder} variables)
    clean, error = sanitize_translation(value)
    if error:
        raise ValueError(error)
"""

from __future__ import annotations

import re

# ── Constants ────────────────────────────────────────────────────────────

# Maximum lengths for different field types
MAX_TEXT_LENGTH = 5_000
MAX_TRANSLATION_LENGTH = 10_000
MAX_SHORT_TEXT_LENGTH = 500

# Known placeholder variables used across translations.
# Only these ``{name}`` patterns are allowed in translation values.
ALLOWED_TRANSLATION_VARIABLES = frozenset({
    "name", "count", "limit", "max", "realm", "date", "time",
    "email", "username", "role", "guild", "event", "character",
    "size", "minutes", "hours", "days", "resource", "plan",
    "current", "total", "remaining", "used", "percent",
    "min", "max_length", "provider", "url", "version",
    "action", "target", "source", "status", "type",
    "error", "message", "code", "field", "fields",
    "value", "label", "title", "description",
    # Vue i18n linked-message escaping: {'@'} etc.
    "'@'",
})

# Translation variable examples for documentation
TRANSLATION_VARIABLE_EXAMPLES: dict[str, str] = {
    "name": "User or guild name — e.g. 'Welcome, {name}!'",
    "count": "Numeric count — e.g. '{count} members online'",
    "limit": "Limit value — e.g. 'Maximum {limit} guilds'",
    "max": "Maximum value — e.g. '{count}/{max} slots used'",
    "realm": "Realm name — e.g. 'Playing on {realm}'",
    "date": "Date string — e.g. 'Expires on {date}'",
    "time": "Time string — e.g. 'Starts at {time}'",
    "email": "Email address — e.g. 'Sent to {email}'",
    "username": "Username — e.g. 'Logged in as {username}'",
    "role": "Role name — e.g. 'Assigned role: {role}'",
    "guild": "Guild name — e.g. 'You joined {guild}'",
    "event": "Event name — e.g. 'Signed up for {event}'",
    "character": "Character name — e.g. '{character} removed'",
    "size": "Raid size — e.g. '{size}-player raid'",
    "minutes": "Duration — e.g. '{minutes} minutes late'",
    "resource": "Resource type — e.g. 'Limit for {resource}'",
    "plan": "Plan name — e.g. 'Current plan: {plan}'",
    "status": "Status value — e.g. 'Status: {status}'",
    "field": "Field name — e.g. '{field} is required'",
    "fields": "Field names — e.g. 'Missing: {fields}'",
}

# Valid translation key pattern: dotted alphanumeric segments
TRANSLATION_KEY_PATTERN = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$"
)
MAX_KEY_LENGTH = 255


# ── Dangerous content patterns ───────────────────────────────────────────

_DANGEROUS_PATTERNS: list[re.Pattern] = [
    # HTML / XSS injection
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
    re.compile(r"<\s*link\b", re.IGNORECASE),
    re.compile(r"<\s*style\b", re.IGNORECASE),
    re.compile(r"<\s*img\b[^>]*\bonerror\b", re.IGNORECASE),
    re.compile(r"<\s*svg\b[^>]*\bonload\b", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(
        r"on(error|load|click|mouseover|focus|blur|submit|change)\s*=",
        re.IGNORECASE,
    ),
    # Shell / OS escape attempts
    re.compile(r"\$\("),                       # $(command)
    re.compile(r"`[^`]+`"),                    # `command`
    re.compile(r"\$\{[^}]*\}"),                # ${var} — shell expansion
    re.compile(
        r";\s*(rm|cat|ls|wget|curl|bash|sh|python|node|exec|eval)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\|\s*(bash|sh|python|node)\b", re.IGNORECASE),
    re.compile(r">\s*/"),                       # redirect to filesystem
    # Encoding-based obfuscation
    re.compile(r"\\x[0-9a-fA-F]{2}"),          # hex escapes
    re.compile(r"\\u[0-9a-fA-F]{4}"),          # unicode escapes
    re.compile(r"&#\d+;"),                      # HTML numeric entities
    re.compile(r"&#x[0-9a-fA-F]+;"),            # HTML hex entities
]

_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")


# ── Public API ───────────────────────────────────────────────────────────


def check_dangerous_content(value: str) -> str | None:
    """Check if a string contains dangerous patterns.

    Returns an error message if dangerous content is found, ``None`` otherwise.
    """
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(value):
            return (
                "Value contains potentially dangerous content. "
                "HTML tags, script injection, shell commands, and escape "
                "sequences are not allowed."
            )
    return None


def sanitize_text(
    value: str,
    *,
    max_length: int = MAX_TEXT_LENGTH,
    field_name: str = "Value",
) -> tuple[str, str | None]:
    """Sanitize general user-provided text (descriptions, notes, etc.).

    Returns ``(sanitized_value, error_message)``.  If *error_message* is
    not ``None`` the value was rejected.

    This does NOT validate ``{placeholder}`` variables — use
    :func:`sanitize_translation` for translation values.
    """
    if not isinstance(value, str):
        return "", f"{field_name} must be a string"

    value = value.strip()

    if len(value) > max_length:
        return "", f"{field_name} must be at most {max_length:,} characters"

    error = check_dangerous_content(value)
    if error:
        return "", error

    return value, None


def sanitize_translation(
    value: str,
    *,
    max_length: int = MAX_TRANSLATION_LENGTH,
    allowed_variables: frozenset[str] | None = None,
) -> tuple[str, str | None]:
    """Sanitize a translation value with placeholder validation.

    In addition to the checks in :func:`sanitize_text`, this validates
    that only whitelisted ``{variable}`` placeholders are used.

    Returns ``(sanitized_value, error_message)``.
    """
    if allowed_variables is None:
        allowed_variables = ALLOWED_TRANSLATION_VARIABLES

    sanitized, error = sanitize_text(value, max_length=max_length)
    if error:
        return sanitized, error

    # Validate placeholder variables
    placeholders = _PLACEHOLDER_RE.findall(sanitized)
    for placeholder in placeholders:
        if placeholder not in allowed_variables:
            allowed_list = sorted(allowed_variables - {"'@'"})
            return "", (
                f"Unknown placeholder variable '{{{placeholder}}}'. "
                f"Allowed variables: {', '.join(allowed_list)}"
            )

    return sanitized, None


def validate_translation_key(key: str) -> str | None:
    """Validate a translation key format.

    Returns an error message if invalid, ``None`` if valid.
    """
    if not key or not key.strip():
        return "Translation key cannot be empty"
    key = key.strip()
    if len(key) > MAX_KEY_LENGTH:
        return f"Translation key must be at most {MAX_KEY_LENGTH} characters"
    if not TRANSLATION_KEY_PATTERN.match(key):
        return (
            "Invalid key format. Keys must be dot-separated alphanumeric "
            "segments (e.g. 'admin.translations.saved')"
        )
    return None


def get_allowed_translation_variables() -> list[str]:
    """Return sorted list of allowed translation placeholder variables."""
    return sorted(ALLOWED_TRANSLATION_VARIABLES - {"'@'"})
