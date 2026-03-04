# Plugin Developer Guide

This document describes how to create plugins for the WoTLK Calendar application.

## Architecture Overview

The plugin framework is a lightweight registry system:

- **`BasePlugin`** (`app/plugins/base.py`) — Abstract base class all plugins inherit from.
- **`PluginRegistry`** (`app/plugins/base.py`) — Singleton registry that manages plugin lifecycle.
- **Plugin API** (`app/api/v2/plugins.py`) — REST endpoints for listing and querying plugins.

## Creating a Plugin

### 1. Create the Plugin Directory

```
app/plugins/your_plugin/
├── __init__.py      # (optional, can be empty)
└── plugin.py        # Plugin class definition
```

### 2. Define the Plugin Class

```python
# app/plugins/your_plugin/plugin.py

from __future__ import annotations
from typing import TYPE_CHECKING
from app.plugins.base import BasePlugin

if TYPE_CHECKING:
    from flask import Flask


class YourPlugin(BasePlugin):
    """Description of what your plugin does."""

    key = "your_plugin"           # Unique identifier (lowercase, underscores)
    display_name = "Your Plugin"  # Human-readable name
    version = "1.0.0"
    description = "A brief description of the plugin's purpose."
    plugin_type = "integration"   # "integration" or "expansion"
    dependencies: list[str] = []  # Keys of plugins this depends on

    def get_feature_flags(self) -> dict[str, bool]:
        """Return feature flags this plugin provides."""
        return {
            "your_feature": True,
        }

    def get_default_config(self) -> dict:
        """Return default configuration for admin UI."""
        return {
            "setting_a": "default_value",
        }

    def register_blueprints(self, app: "Flask") -> None:
        """Register any Flask blueprints this plugin provides."""
        # from app.plugins.your_plugin.routes import bp
        # app.register_blueprint(bp, url_prefix="/api/v2/your-plugin")
        pass

    def on_guild_enable(self, guild_id: int) -> None:
        """Called when a guild enables this plugin."""
        pass

    def on_guild_disable(self, guild_id: int) -> None:
        """Called when a guild disables this plugin."""
        pass
```

### 3. Register the Plugin

Add your plugin to `PluginRegistry.init_app()` in `app/plugins/base.py`:

```python
@classmethod
def init_app(cls, app: "Flask") -> None:
    if cls._initialised:
        return

    from app.plugins.armory.plugin import ArmoryPlugin
    from app.plugins.discord.plugin import DiscordPlugin
    from app.plugins.your_plugin.plugin import YourPlugin  # Add this

    cls.register(ArmoryPlugin())
    cls.register(DiscordPlugin())
    cls.register(YourPlugin())  # Add this

    for plugin in cls._plugins.values():
        plugin.register_blueprints(app)

    cls._initialised = True
```

## BasePlugin API Reference

| Method | Description |
|--------|-------------|
| `key` | Unique string identifier for the plugin |
| `display_name` | Human-readable name shown in admin UI |
| `version` | Semver version string |
| `description` | Brief description of plugin purpose |
| `plugin_type` | `"integration"` or `"expansion"` |
| `dependencies` | List of plugin keys this plugin depends on |
| `get_feature_flags()` | Returns `dict[str, bool]` of feature flags |
| `get_default_config()` | Returns default config dict for admin |
| `register_blueprints(app)` | Register Flask blueprints during app init |
| `on_guild_enable(guild_id)` | Hook called when guild enables plugin |
| `on_guild_disable(guild_id)` | Hook called when guild disables plugin |
| `to_dict()` | Serialize metadata for API responses |

## PluginRegistry API Reference

| Method | Description |
|--------|-------------|
| `register(plugin)` | Register a plugin instance |
| `get(key)` | Get plugin by key, or `None` |
| `all()` | Get dict of all registered plugins |
| `list_keys()` | Get sorted list of plugin keys |
| `init_app(app)` | Auto-discover and register all plugins |
| `reset()` | Clear registry (used in tests) |

## REST API Endpoints

All endpoints require authentication (`@login_required`).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v2/plugins/` | User | List all registered plugins |
| GET | `/api/v2/plugins/<key>` | User | Get single plugin metadata |
| GET | `/api/v2/plugins/<key>/config` | `manage_plugins` | Get plugin config |
| GET | `/api/v2/plugins/armory/providers` | User | List armory providers |
| GET | `/api/v2/plugins/armory/providers/<name>/realms` | User | Get provider realms |

## Built-in Plugins

### Armory Plugin (`armory`)

The generic armory integration plugin wraps the pluggable armory provider
system (`app/services/armory/`). It provides:

- Character lookup and guild sync
- Dynamic realm discovery from providers
- Support for multiple armory providers (e.g., Warmane)

**Feature Flags:**
- `character_sync` — Enable character synchronization
- `armory_integration` — Enable armory lookups
- `realm_suggestions` — Enable dynamic realm suggestions

**Armory Providers:**
Providers live in `app/services/armory/` and implement the `ArmoryProvider`
base class. Each provider must implement:
- `fetch_realms()` — Dynamically fetch available realms
- `get_default_realms()` — Return static fallback realm list
- `lookup_character(name, realm)` — Look up a character
- `lookup_guild(name, realm)` — Look up a guild

### Discord Plugin (`discord`)

Discord OAuth2 integration for user authentication. Provides:

- Login via Discord account
- Discord ID linking to user profiles

**Feature Flags:**
- `discord_login` — Enable Discord OAuth2 login

## Frontend Integration

Plugins are displayed in the **Plugins tab** of the Global Admin panel
(`src/components/admin/PluginsTab.vue`).

The frontend API module (`src/api/plugins.js`) provides:

```javascript
import * as pluginsApi from '@/api/plugins'

// List all plugins
const plugins = await pluginsApi.listPlugins()

// Get single plugin
const plugin = await pluginsApi.getPlugin('armory')

// Get plugin config (admin only)
const config = await pluginsApi.getPluginConfig('armory')
```

## Testing Plugins

Use `PluginRegistry.reset()` in test fixtures to clear state between tests:

```python
from app.plugins.base import PluginRegistry

@pytest.fixture(autouse=True)
def reset_plugins():
    PluginRegistry.reset()
    yield
    PluginRegistry.reset()
```

See `tests/test_plugins.py` for comprehensive examples of plugin testing
patterns including registration, feature flags, config endpoints, and
armory provider integration.

## Permissions

Plugin management requires the `manage_plugins` system permission, which
is assigned to the `global_admin` role by default.

The permission is defined in `app/seeds/permissions.py` and enforced
via `require_system_permission("manage_plugins")` in the plugin config
endpoint.
