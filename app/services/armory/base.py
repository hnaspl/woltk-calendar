"""Abstract base class for armory providers."""

from __future__ import annotations

import abc
from typing import Optional


class ArmoryProvider(abc.ABC):
    """Base class that every armory provider must implement."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Short identifier for this provider (e.g. 'warmane')."""

    @property
    @abc.abstractmethod
    def api_base_url(self) -> str:
        """Root URL of the provider's API."""

    @abc.abstractmethod
    def fetch_character(self, realm: str, name: str) -> Optional[dict]:
        """Fetch character data from the provider.

        Returns a raw API response dict or ``None`` on failure.
        """

    @abc.abstractmethod
    def fetch_guild(self, realm: str, guild_name: str) -> Optional[dict]:
        """Fetch guild roster data from the provider.

        Returns a raw API response dict or ``None`` on failure.
        """

    @abc.abstractmethod
    def build_character_dict(self, data: dict, realm: str) -> dict:
        """Transform a raw API response into a normalised character dict."""

    @abc.abstractmethod
    def build_armory_url(self, realm: str, name: str) -> str:
        """Build a user-facing armory URL for a character."""

    def get_default_realms(self) -> list[str]:
        """Return the provider's known realm list.

        The base implementation returns an empty list.  Providers that
        can discover realms dynamically (e.g. via their API) should
        override this.  Guilds manage their own realm lists via the
        :class:`GuildRealm` model; this method is only used as optional
        realm *suggestions*.
        """
        return []

    def fetch_realms(self) -> list[str]:
        """Attempt to fetch available realms from the provider's API.

        Returns an empty list if the provider does not support dynamic
        realm discovery.  Subclasses may override to query their API.
        """
        return []
