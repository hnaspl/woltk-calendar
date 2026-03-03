"""Provider registry for armory backends.

Providers are registered by name and can be looked up at runtime so that
different guilds / configurations can use different armory APIs.
"""

from __future__ import annotations

from typing import Type

from app.services.armory.base import ArmoryProvider

_registry: dict[str, Type[ArmoryProvider]] = {}
_builtins_registered = False


def register_provider(name: str, cls: Type[ArmoryProvider]) -> None:
    """Register *cls* under *name* (case-insensitive)."""
    _registry[name.lower()] = cls


def _ensure_builtins() -> None:
    """Lazily register built-in providers on first access."""
    global _builtins_registered
    if not _builtins_registered:
        from app.services.armory.warmane import WarmaneProvider
        register_provider("warmane", WarmaneProvider)
        _builtins_registered = True


def get_provider(name: str, **kwargs) -> ArmoryProvider:
    """Return an instance of the provider registered under *name*.

    Extra *kwargs* are forwarded to the provider constructor.
    Raises ``KeyError`` if the name is not registered.
    """
    _ensure_builtins()
    cls = _registry.get(name.lower())
    if cls is None:
        raise KeyError(f"Unknown armory provider: {name!r}")
    return cls(**kwargs)


def list_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    _ensure_builtins()
    return sorted(_registry)
