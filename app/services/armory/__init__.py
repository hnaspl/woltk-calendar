"""Armory provider package — pluggable armory backend system.

Quick-start::

    from app.services.armory import get_provider, list_providers

    provider = get_provider("warmane")
    data = provider.fetch_character("Icecrown", "Arthas")
"""

from app.services.armory.base import ArmoryProvider
from app.services.armory.registry import get_provider, list_providers, register_provider
from app.services.armory.warmane import WarmaneProvider

__all__ = [
    "ArmoryProvider",
    "WarmaneProvider",
    "get_provider",
    "list_providers",
    "register_provider",
]
