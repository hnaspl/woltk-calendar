"""Armory provider package — fully generic, pluggable armory backend system.

Quick-start::

    from app.services.armory import get_provider, list_providers

    provider = get_provider("armory")
    data = provider.fetch_character("SomeRealm", "SomeName")

Providers are registered by plugins during application startup.
The registry itself has no knowledge of any specific server.
"""

from app.services.armory.base import ArmoryProvider
from app.services.armory.registry import (
    get_provider,
    list_providers,
    register_provider,
    register_domain,
)

__all__ = [
    "ArmoryProvider",
    "get_provider",
    "list_providers",
    "register_provider",
    "register_domain",
]
