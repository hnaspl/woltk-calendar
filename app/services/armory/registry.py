"""Provider registry for armory backends.

Providers are registered by name and can be looked up at runtime so that
different guilds / configurations can use different armory APIs.

The registry is **fully generic** — it has no knowledge of any specific
server.  Providers register themselves via their plugins during
application startup.
"""

from __future__ import annotations

from typing import Optional, Type
from urllib.parse import urlparse

from app.services.armory.base import ArmoryProvider

_registry: dict[str, Type[ArmoryProvider]] = {}

# Maps known armory domains to provider names for auto-detection.
# Populated dynamically by plugins via register_domain().
_DOMAIN_TO_PROVIDER: dict[str, str] = {}


def register_provider(name: str, cls: Type[ArmoryProvider]) -> None:
    """Register *cls* under *name* (case-insensitive)."""
    _registry[name.lower()] = cls


def register_domain(domain: str, provider_name: str) -> None:
    """Map *domain* to *provider_name* for URL-based auto-detection."""
    _DOMAIN_TO_PROVIDER[domain.lower()] = provider_name.lower()


def get_provider(name: str, **kwargs) -> ArmoryProvider:
    """Return an instance of the provider registered under *name*.

    Extra *kwargs* are forwarded to the provider constructor.
    Raises ``KeyError`` if the name is not registered.
    """
    cls = _registry.get(name.lower())
    if cls is None:
        raise KeyError(f"Unknown armory provider: {name!r}")
    return cls(**kwargs)


def list_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(_registry)


def detect_provider_from_url(url: str) -> Optional[str]:
    """Detect armory provider name from a URL.

    Parses the hostname and checks it against domains registered by
    plugins via :func:`register_domain`.
    Returns the provider name or ``None`` if no match.
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        return _DOMAIN_TO_PROVIDER.get(host)
    except (ValueError, AttributeError):
        return None


def reset() -> None:
    """Clear the registry — used in tests."""
    _registry.clear()
    _DOMAIN_TO_PROVIDER.clear()
