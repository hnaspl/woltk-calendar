# Translations

Translation files for the WotLK Raid Calendar application.
Both the Flask backend (`app/i18n.py`) and the Vue frontend (`src/i18n.js`)
load from the same JSON files.

Supported locales: **en** (English), **pl** (Polish).

---

## Variable Reference

Translation strings use `{variable}` placeholders for dynamic content.
Below is a reference of every variable available for use in translations.

| Variable | Description |
|---|---|
| `{character}` | Character name (e.g. "Arthas") |
| `{characters}` | Comma-separated list of character names |
| `{count}` | Numeric count (items, guilds, members, etc.) |
| `{countdown}` | Countdown timer in seconds |
| `{event}` | Short event/raid title |
| `{eventTitle}` | Full event/raid title (may appear inside quotes in the string) |
| `{failed}` | Number of failed operations |
| `{fields}` | Comma-separated list of missing field names |
| `{guild}` | Guild name |
| `{guildName}` | Full guild name |
| `{guildTag}` | Guild tag / abbreviation (e.g. "[ABC]") |
| `{key}` | Setting or field key name |
| `{n}` | Numeric value (e.g. number of days) |
| `{name}` | Display name — character, role, template, etc. |
| `{newCharacter}` | Replacement character name |
| `{newRole}` | New role name after a change |
| `{note}` | Optional note text (may be empty) |
| `{officer}` | Officer's display name who performed the action |
| `{oldCharacter}` | Original character being replaced |
| `{oldRole}` | Previous role name before a change |
| `{outcome}` | Attendance outcome label (Attended / Late / Unattended) |
| `{position}` | Queue position number |
| `{query}` | Search query entered by the user |
| `{reason}` | Optional reason text (may be empty, prefixed with space) |
| `{role}` | Role name (e.g. "Tank", "Healer", "Officer") |
| `{size}` | Raid size number (e.g. 10, 25) |
| `{starts}` | Formatted start date/time string |
| `{succeeded}` | Number of successful operations |
| `{time}` | Formatted time string |
| `{total}` | Total count or sum |
| `{username}` | User's username |

### Usage examples

```json
"welcome": "Welcome back, {name}!",
"copiedSuccess": "\"{name}\" copied to {count} guild(s)",
"missingFields": "Missing fields: {fields}",
"signupConfirmed": "Your character {character} is signed up as {role} in {eventTitle}."
```

---

## Key Organization

Translation keys are organized into these top-level sections:

| Section | Purpose |
|---|---|
| `common.buttons` | Shared button labels (Save, Cancel, Delete, etc.) |
| `common.status` | Status labels (Open, Locked, Completed, etc.) |
| `common.labels` | Shared UI labels (Guild, Class, Characters, Loading, etc.) |
| `common.fields` | Shared form field labels (Role, Status, Realm, etc.) |
| `common.time` | Time-related labels |
| `common.errors` | HTTP error messages |
| `common.toasts` | Shared toast notification messages |
| `common.copy` | Copy-to-guilds flow strings |
| `nav` | Navigation menu items |
| `auth` | Authentication (login, register, password) |
| `profile` | User profile page |
| `dashboard` | Dashboard view |
| `calendar` | Calendar view and event creation |
| `raidDetail` | Raid detail / event page |
| `characters` | Character management |
| `attendance` | Attendance tracking |
| `signup` / `signupList` | Signup form and signup list |
| `lineup` / `composition` | Lineup board and composition |
| `guild` | Guild creation and settings |
| `guildSettings` | Guild settings page (toasts) |
| `members` | Member management |
| `roles` | Role and permission management |
| `raidDefinitions` | Raid definition management |
| `templates` | Template management |
| `series` | Recurring raid series |
| `admin` | Admin panel (users, system, guild settings tabs) |
| `notifications` | Notification bell UI |
| `notify` | Notification content templates (used by backend) |
| `api` | Backend API response messages |
| `warmane` | Warmane API integration messages |
| `topBar` | Top navigation bar |
| `characterDetail` | Character detail modal |

### Unification rules

- **Single words / common phrases** → use `common.*` keys (e.g. `common.fields.role` instead of per-section `role` keys).
- **Toast messages** → use `common.toasts.*` for shared messages, section-specific `*.toasts.*` for unique ones.
- **Buttons** → use `common.buttons.*` for all standard button labels.
- **Status labels** → use `common.status.*` for all status values.
- **No emoji or icons** in translation strings — keep those in Vue templates.
