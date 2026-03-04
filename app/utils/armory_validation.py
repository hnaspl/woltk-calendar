"""Armory URL validation — prevent malicious URLs in armory configurations.

Only URLs that look like legitimate WoW private-server armory APIs are
accepted.  The check enforces:

1. Valid HTTP/HTTPS scheme
2. A real hostname (no IP addresses, no ``localhost``)
3. Path must be ``/api`` or empty (the actual API root)
4. No query strings, fragments, or credentials in the URL

Global admins can extend the allowed-domains list via the
``armory_allowed_domains`` system setting (comma-separated).  When the
setting is empty **any** domain is accepted as long as rules 1-4 pass,
giving maximum flexibility for self-hosted armory servers.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


# No domains are hardcoded — admins configure allowed domains via settings.
# When the setting is empty, any domain is accepted (open mode).
_BUILTIN_DOMAINS: frozenset[str] = frozenset()

# Reject obviously dangerous hostnames
_BLOCKED_HOSTS: re.Pattern = re.compile(
    r"^(localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|::1|\[::1\])$",
    re.IGNORECASE,
)

# Only allow IP-like hostnames to be caught — we want real domain names
_IP_PATTERN: re.Pattern = re.compile(
    r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
)


def validate_armory_url(url: str, extra_allowed_domains: list[str] | None = None) -> str | None:
    """Validate an armory API base URL.

    Returns ``None`` if the URL is valid, or an error message string
    describing why it was rejected.

    Parameters
    ----------
    url:
        The URL to validate (e.g. ``http://armory.example.com/api``).
    extra_allowed_domains:
        Optional list of additional allowed domain names loaded from
        the ``armory_allowed_domains`` system setting.
    """
    if not url or not isinstance(url, str):
        return "URL is required"

    url = url.strip()

    # ---- parse ----
    try:
        parsed = urlparse(url)
    except ValueError:
        return "Invalid URL format"

    # ---- scheme ----
    if parsed.scheme not in ("http", "https"):
        return "URL must use http or https"

    # ---- hostname ----
    host = (parsed.hostname or "").lower()
    if not host:
        return "URL must include a hostname"

    if _BLOCKED_HOSTS.match(host):
        return "localhost and loopback addresses are not allowed"

    if _IP_PATTERN.match(host):
        return "IP addresses are not allowed — use a domain name"

    # Must have at least one dot (real domain)
    if "." not in host:
        return "Hostname must be a valid domain name"

    # ---- no credentials ----
    if parsed.username or parsed.password:
        return "URL must not contain credentials"

    # ---- no query / fragment ----
    if parsed.query:
        return "URL must not contain query parameters"
    if parsed.fragment:
        return "URL must not contain a fragment"

    # ---- path should be /api or empty ----
    path = parsed.path.rstrip("/")
    if path and path != "/api":
        return "URL path must be empty or /api"

    # ---- domain allow-list (optional) ----
    allowed = set(_BUILTIN_DOMAINS)
    if extra_allowed_domains:
        for d in extra_allowed_domains:
            d = d.strip().lower()
            if d:
                allowed.add(d)

    # When the allow-list is just the builtins AND extra_allowed_domains
    # was explicitly provided (meaning the admin set a whitelist), enforce it.
    # If extra_allowed_domains is None we allow any domain (open mode).
    if extra_allowed_domains is not None and host not in allowed:
        return f"Domain '{host}' is not in the allowed armory domains list"

    return None


def get_allowed_domains_from_settings() -> list[str] | None:
    """Load the ``armory_allowed_domains`` system setting.

    Returns ``None`` when the setting does not exist (open mode), or a
    list of domain strings when configured.
    """
    try:
        from app.models.system_setting import SystemSetting
        from app.extensions import db

        row = db.session.get(SystemSetting, "armory_allowed_domains")
        if row is None:
            return None
        val = row.value.strip()
        if not val:
            return None
        return [d.strip().lower() for d in val.split(",") if d.strip()]
    except Exception:
        return None
