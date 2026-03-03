# SaaS Decoupling & Modular Architecture Plan

> **Goal:** Transform woltk-calendar from a single-expansion monolith into a
> modular, pluggable, SaaS-first platform. Define clear core vs. plugin
> boundaries, redesign guild membership for multi-tenant isolation, and
> build an expansion-aware class/role system that supports multiple WoW
> addons (Classic, TBC, WotLK, Cataclysm, MoP, WoD, Legion, BfA,
> Shadowlands, Dragonflight, The War Within).
>
> **Scope:** Planning document only — no code changes in this phase.

---

## Table of Contents

1. [Current Architecture Assessment](#1-current-architecture-assessment)
2. [Core vs. Pluggable Feature Matrix](#2-core-vs-pluggable-feature-matrix)
3. [Guild Membership & Multi-Tenancy Redesign](#3-guild-membership--multi-tenancy-redesign)
4. [Expansion-Aware Class/Role/Spec System](#4-expansion-aware-classrolespec-system)
5. [Class → Role Ability Matrix for Guild Admins](#5-class--role-ability-matrix-for-guild-admins)
6. [Plugin Architecture](#6-plugin-architecture)
7. [Phased Implementation Roadmap](#7-phased-implementation-roadmap)
8. [Migration & Backward Compatibility](#8-migration--backward-compatibility)
9. [Open Questions & Decisions](#9-open-questions--decisions)

---

## 1. Current Architecture Assessment

### 1.1 What Works Well (Keep)

| Area | Status | Notes |
|------|--------|-------|
| Blueprint-per-module API | ✅ Good | 16 blueprints, clean URL prefixes |
| Service ↔ API separation | ✅ Good | Services handle business logic, APIs handle HTTP |
| Permission system | ✅ Good | 43 granular permissions, 5 hierarchical roles, grant rules |
| Feature flags | ✅ Good | `GuildFeature` model with per-guild toggle |
| Real-time events | ✅ Good | Centralized in `app/utils/realtime.py` |
| Notification system | ✅ Good | Centralized in `app/utils/notify.py` |
| Frontend stores | ✅ Good | Clean Pinia separation (auth, guild, calendar, ui, constants) |

### 1.2 What Needs Decoupling

| Area | Issue | Impact |
|------|-------|--------|
| WoW classes | Hardcoded 10 WotLK classes in `WowClass` enum | Cannot support Classic (no DK), MoP+ (Monk), Legion+ (DH) |
| Class specs | Hardcoded WotLK spec names in `CLASS_SPECS` | Specs changed across expansions (e.g., "Combat" → "Outlaw" for Rogue) |
| Class → Role mapping | Hardcoded in `CLASS_ROLES` | Same class has different viable roles across expansions |
| Raid definitions | `WOTLK_RAIDS` constant has only WotLK raids | Other expansions have different raids |
| Warmane coupling | Armory/sync tied to Warmane API | Other private servers and retail WoW use different APIs |
| Guild membership | Open self-join by default (`allow_self_join=True`) | Not SaaS-safe — users can access any guild's data |
| No tenant isolation | Users see all guilds, can join freely | No data boundary between organizations |
| Database name | `wotlk_calendar.db` hardcoded | Naming implies single-expansion |

### 1.3 Current Module Dependency Map

```
API Layer (blueprints)
    ├── auth.py ──────────── auth_service.py
    ├── guilds.py ────────── guild_service.py
    ├── characters.py ────── character_service.py
    ├── events.py ────────── event_service.py
    ├── signups.py ───────── signup_service.py
    ├── lineup.py ────────── lineup_service.py
    ├── attendance.py ────── attendance_service.py
    ├── raid_definitions.py  (direct DB access)
    ├── templates.py ──────  (direct DB access)
    ├── series.py ─────────  (direct DB access)
    ├── warmane.py ────────── warmane_service.py ← Expansion-specific
    ├── armory.py ─────────── armory/ ← Expansion-specific
    ├── notifications.py ──── notification_service.py
    ├── roles.py ──────────  (direct DB access + permission checks)
    └── meta.py ───────────── constants.py ← Expansion-specific
```

---

## 2. Core vs. Pluggable Feature Matrix

### 2.1 Core Platform (Always Present)

These features form the reusable SaaS foundation and must work regardless of
which game expansion or addon is selected.

| Module | Description | Current Location |
|--------|-------------|------------------|
| **Authentication** | User registration, login, sessions, password management | `auth_service.py`, `auth.py` |
| **User management** | User CRUD, activation/deactivation, profile management | `admin.py`, `User` model |
| **Permission system** | Roles, permissions, grant rules, RBAC checks | `permission.py` model, `roles.py` API, `seeds/permissions.py` |
| **Guild/Organization** | Guild CRUD, membership management, settings | `guild_service.py`, `Guild` model |
| **Guild membership** | Join/leave/invite/ban flow with proper isolation | `GuildMembership` model |
| **Feature flags** | Per-guild feature toggles | `feature_service.py`, `GuildFeature` model |
| **Notifications** | Real-time + persistent notification system | `notification_service.py`, Socket.IO |
| **Calendar/Events** | Event CRUD, scheduling, status management | `event_service.py`, `events.py` |
| **Signups** | Event sign-up/decline/manage flow | `signup_service.py` |
| **Lineup & Bench** | Lineup board, bench queue, auto-promote | `lineup_service.py` |
| **Attendance** | Attendance tracking per event | `attendance_service.py` |
| **Templates & Series** | Reusable event templates, recurring series | `templates.py`, `series.py` |
| **Raid Definitions** | Configurable raid/dungeon definitions | `raid_definitions.py` |
| **Background Jobs** | Scheduler + worker queue | `jobs/scheduler.py`, `jobs/worker.py` |
| **System Settings** | Global configuration management | `SystemSetting` model |
| **Meta/Constants API** | Serve dynamic configuration to frontend | `meta.py` |

### 2.2 Pluggable Features (Expansion/Addon-Specific)

These features depend on which game expansion or addon a guild has selected
and should be loaded dynamically.

| Plugin | Description | Depends On | Current Location |
|--------|-------------|------------|------------------|
| **Expansion Pack** | Class/spec/role definitions per expansion | Core meta system | `enums.py`, `constants.py` |
| **Warmane Integration** | Armory sync, character lookup, guild roster import | Expansion Pack | `warmane_service.py`, `armory/` |
| **Character Sync** | Periodic background sync of character data | Armory provider | `character_service.py` (sync parts) |
| **Armory Provider** | Pluggable armory data source (Warmane, TrinityCore, etc.) | Expansion Pack | `armory_config.py` model |
| **Class→Role Matrix** | Which classes can fill which raid roles | Expansion Pack | `CLASS_ROLES` in `constants.py` |
| **Spec Definitions** | Talent tree / spec names per class per expansion | Expansion Pack | `CLASS_SPECS` in `constants.py` |
| **Raid Catalog** | Predefined raid instances per expansion | Expansion Pack | `WOTLK_RAIDS` in `constants.py` |
| **Discord Integration** | Discord bot / webhook notifications | Core notifications | `discord_service.py` |

### 2.3 Feature Flag Extensions

Current feature flags to keep and extend:

```
Current:                    Proposed additions:
─────────                   ─────────────────────
attendance ✓                class_role_matrix ✓ (new)
templates ✓                 multi_spec ✓ (new)
series ✓                    guild_invitations ✓ (new)
character_sync ✓            armory_integration ✓ (new)
notifications ✓             discord_integration ✓ (new)
                            custom_raid_definitions ✓ (new)
```

---

## 3. Guild Membership & Multi-Tenancy Redesign

### 3.1 Problem Statement

Currently, any registered user can:
- See all guilds in the system
- Self-join any guild (if `allow_self_join=True`, which is the default)
- Be a member of multiple guilds simultaneously

This is **not SaaS-safe** because:
- No data isolation between guilds/organizations
- No control over who accesses guild data
- No billing boundary per organization
- Guild admins cannot control their membership

### 3.2 Proposed Solution: Invitation-Based Guild Membership

**Recommendation:** Implement an **invitation-only** model with optional public
guild discovery, rather than a full tenant isolation model.

**Rationale for invitation-based over strict tenants:**
- WoW players often belong to multiple guilds (main + alt guilds, PvP guilds, social guilds)
- Strict tenant isolation would prevent cross-guild participation
- Invitation model gives guild admins control while keeping flexibility
- Simpler to implement than full multi-tenancy
- Can add tenant boundaries later for enterprise/billing use cases

#### 3.2.1 Membership Flow (Proposed)

```
                                    ┌─────────────────────┐
                                    │   Guild Admin        │
                                    │   creates guild      │
                                    └──────────┬──────────┘
                                               │
                              ┌────────────────┴────────────────┐
                              │                                  │
                     ┌────────▼─────────┐             ┌─────────▼────────┐
                     │ INVITATION MODE   │             │ APPLICATION MODE │
                     │ (default for SaaS)│             │ (optional)       │
                     └────────┬─────────┘             └─────────┬────────┘
                              │                                  │
                    ┌─────────▼──────────┐             ┌────────▼─────────┐
                    │ Admin sends invite │             │ User browses     │
                    │ (email / link /    │             │ public guilds &  │
                    │  in-app)           │             │ sends application│
                    └─────────┬──────────┘             └────────┬─────────┘
                              │                                  │
                    ┌─────────▼──────────┐             ┌────────▼─────────┐
                    │ User accepts       │             │ Admin approves   │
                    │ → status: ACTIVE   │             │ → status: ACTIVE │
                    └────────────────────┘             └──────────────────┘
```

#### 3.2.2 New Membership Statuses

Extend current `MemberStatus` enum:

```python
class MemberStatus(str, Enum):
    ACTIVE = "active"          # Full member (existing)
    INVITED = "invited"        # Invited, pending acceptance (existing)
    BANNED = "banned"          # Banned from guild (existing)
    APPLIED = "applied"              # NEW: User applied, pending admin approval
    INVITE_DECLINED = "invite_declined"   # NEW: User declined an invitation
    APPLICATION_REJECTED = "application_rejected"  # NEW: Admin rejected an application
```

#### 3.2.3 Guild Visibility Settings

New guild-level settings to control discovery and access:

```python
class GuildVisibility(str, Enum):
    PRIVATE = "private"      # Not discoverable, invitation-only
    LISTED = "listed"        # Visible in directory, but requires invitation/application
    PUBLIC = "public"        # Visible and allows self-join (current behavior)
```

#### 3.2.4 Invitation Model

New `GuildInvitation` model:

```
GuildInvitation
├── id (PK)
├── guild_id (FK → Guild)
├── inviter_id (FK → User)         # Who sent the invite
├── invitee_email (String)         # Email of invitee (may not have account yet)
├── invitee_user_id (FK → User)    # Auto-resolved if email matches existing user;
│                                  #   otherwise set when invitee registers & accepts
├── invite_token (String, unique)  # Unique token for invite link
├── role (String)                  # Role to assign on acceptance
├── status (Enum)                  # pending / accepted / invite_declined / expired
├── expires_at (DateTime)          # Invitation expiry
├── created_at (DateTime)
├── accepted_at (DateTime)
```

#### 3.2.5 New Permissions for Membership Control

```python
# Add to ALL_PERMISSIONS in seeds/permissions.py:
("invite_members", "Invite Members", "Send guild invitations", "guild"),
("approve_applications", "Approve Applications", "Approve/decline membership applications", "guild"),
("manage_guild_visibility", "Manage Guild Visibility", "Change guild visibility settings", "guild"),
```

#### 3.2.6 Data Access Boundaries

Even without strict tenant isolation, enforce guild-scoped data access:

| Data | Current Access | Proposed Access |
|------|---------------|-----------------|
| Guild list | All guilds visible | Only joined + public guilds |
| Guild details | Any authenticated user | Members only (or listed summary) |
| Events | Visible to all guild members | Visible to active members only |
| Characters | Visible across guilds | Scoped to guild context |
| Attendance | Guild-scoped | Guild-scoped (enforce) |
| Notifications | User-scoped | User + guild-scoped |

### 3.3 Why Not Full Multi-Tenancy?

| Approach | Pros | Cons |
|----------|------|------|
| **Full tenant isolation** (DB per tenant) | Complete data separation, easy billing | Heavy infrastructure, no cross-guild features, complex migrations |
| **Schema-based multi-tenancy** (schema per tenant) | Good isolation, shared infrastructure | Complex queries, migration headaches |
| **Row-level tenancy** (tenant_id on every table) | Simple, allows cross-tenant features | Must enforce on every query, risk of data leaks |
| **Invitation-based membership** ✅ | Simple, flexible, matches WoW guild model | Less strict isolation, needs careful permission enforcement |

**Decision:** Start with **invitation-based membership** (3.2) which gives guild
admins control while keeping the flexibility WoW players need. Add row-level
tenancy boundaries later only if needed for enterprise billing features.

---

## 4. Expansion-Aware Class/Role/Spec System

### 4.1 WoW Expansion Class Availability Research

Below is the complete class availability matrix across all WoW expansions
(private servers and retail). This is critical for the multi-addon support.

| Class | Classic | TBC | WotLK | Cata | MoP | WoD | Legion | BfA | SL | DF | TWW |
|-------|---------|-----|-------|------|-----|-----|--------|-----|----|----|-----|
| Warrior | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Paladin | ✅¹ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hunter | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Rogue | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Priest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Shaman | ✅² | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mage | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Warlock | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Druid | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Death Knight | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Monk | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Demon Hunter | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Evoker | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

> ¹ Classic: Paladin was Alliance-only  
> ² Classic: Shaman was Horde-only  

### 4.2 Spec Changes Across Expansions

Notable spec name and structure changes:

| Class | WotLK Spec | Changed In | New Name |
|-------|-----------|------------|----------|
| Rogue | Combat | Legion 7.0 | Outlaw |
| Druid | Feral Combat | Cataclysm 4.0 | Feral (split into Feral + Guardian) |
| Druid | (none) | Cataclysm 4.0 | Guardian (new 4th spec) |
| Hunter | (all 3 ranged) | Legion 7.0 | Survival became melee |
| Death Knight | Blood/Frost/Unholy (all can tank/DPS) | Cataclysm 4.0 | Blood = tank only, Frost/Unholy = DPS only |
| Monk | (N/A) | MoP 5.0 | Brewmaster / Windwalker / Mistweaver |
| Demon Hunter | (N/A) | Legion 7.0 | Havoc / Vengeance |
| Evoker | (N/A) | Dragonflight 10.0 | Devastation / Preservation / Augmentation³ |

> ³ Augmentation spec added in DF 10.1.5

### 4.3 Class → Role Mapping by Expansion

Each expansion may change which roles a class can perform:

| Class | Classic/TBC Roles | WotLK Roles | Cata+ Roles | Legion+ Roles |
|-------|-------------------|-------------|-------------|---------------|
| Warrior | Tank, Melee DPS | Tank, Melee DPS | Tank, Melee DPS | Tank, Melee DPS |
| Paladin | Healer, Tank⁴, Melee DPS | Healer, Tank, Melee DPS | Healer, Tank, Melee DPS | Healer, Tank, Melee DPS |
| Hunter | Ranged DPS | Ranged DPS | Ranged DPS | Ranged DPS, Melee DPS⁵ |
| Rogue | Melee DPS | Melee DPS | Melee DPS | Melee DPS |
| Priest | Healer, Ranged DPS | Healer, Ranged DPS | Healer, Ranged DPS | Healer, Ranged DPS |
| Shaman | Healer, Melee DPS, Ranged DPS | Healer, Melee DPS, Ranged DPS | Healer, Melee DPS, Ranged DPS | Healer, Melee DPS, Ranged DPS |
| Mage | Ranged DPS | Ranged DPS | Ranged DPS | Ranged DPS |
| Warlock | Ranged DPS | Ranged DPS | Ranged DPS | Ranged DPS |
| Druid | Healer, Tank, Melee DPS, Ranged DPS | Healer, Tank, Melee DPS, Ranged DPS | Healer, Tank, Melee DPS, Ranged DPS | Healer, Tank, Melee DPS, Ranged DPS |
| Death Knight | — | Tank, Melee DPS | Tank⁶, Melee DPS | Tank, Melee DPS |
| Monk | — | — | — (MoP+) Tank, Healer, Melee DPS | Tank, Healer, Melee DPS |
| Demon Hunter | — | — | — | Tank, Melee DPS |
| Evoker | — | — | — | — (DF+) Ranged DPS, Healer, Support⁷ |

> ⁴ Paladin tanking in Classic was viable but not meta  
> ⁵ Survival Hunter became melee in Legion  
> ⁶ In Cata+, only Blood can tank (Frost/Unholy lost tank viability)  
> ⁷ Augmentation Evoker is a support/DPS hybrid  

### 4.4 Proposed Data Architecture

#### 4.4.1 Expansion Registry

Replace hardcoded `WowClass` enum with a database-driven or config-driven
expansion registry:

```python
# New: app/expansions/ directory
# Each expansion is a configuration module

EXPANSION_REGISTRY = {
    "classic": {
        "display_name": "Classic (Vanilla)",
        "version": "1.x",
        "classes": ["Warrior", "Paladin", "Hunter", "Rogue", "Priest",
                    "Shaman", "Mage", "Warlock", "Druid"],
        "class_specs": {
            "Warrior": ["Arms", "Fury", "Protection"],
            "Paladin": ["Holy", "Protection", "Retribution"],
            "Hunter": ["Beast Mastery", "Marksmanship", "Survival"],
            "Rogue": ["Assassination", "Combat", "Subtlety"],
            "Priest": ["Discipline", "Holy", "Shadow"],
            "Shaman": ["Elemental", "Enhancement", "Restoration"],
            "Mage": ["Arcane", "Fire", "Frost"],
            "Warlock": ["Affliction", "Demonology", "Destruction"],
            "Druid": ["Balance", "Feral Combat", "Restoration"],
        },
        "class_roles": {
            "Warrior": ["main_tank", "off_tank", "melee_dps"],
            "Paladin": ["main_tank", "off_tank", "healer", "melee_dps"],
            "Hunter": ["range_dps"],
            "Rogue": ["melee_dps"],
            "Priest": ["healer", "range_dps"],
            "Shaman": ["healer", "melee_dps", "range_dps"],
            "Mage": ["range_dps"],
            "Warlock": ["range_dps"],
            "Druid": ["main_tank", "off_tank", "healer", "melee_dps", "range_dps"],
        },
        "raids": [...],  # MC, BWL, AQ40, Naxx40, etc.
    },
    "tbc": {
        "display_name": "The Burning Crusade",
        "version": "2.x",
        "classes": [...],  # Same as Classic
        "class_specs": {...},
        "class_roles": {...},
        "raids": [...],  # Karazhan, SSC, TK, BT, Sunwell, etc.
    },
    "wotlk": {
        "display_name": "Wrath of the Lich King",
        "version": "3.x",
        "classes": ["Warrior", "Paladin", "Hunter", "Rogue", "Priest",
                    "Shaman", "Mage", "Warlock", "Druid", "Death Knight"],
        "class_specs": {
            # Current CLASS_SPECS content
        },
        "class_roles": {
            # Current CLASS_ROLES content
        },
        "raids": [
            # Current WOTLK_RAIDS content
        ],
    },
    "cataclysm": {
        "display_name": "Cataclysm",
        "version": "4.x",
        "classes": [...],  # Same as WotLK but Druid gains Guardian spec
        "class_specs": {
            # Note: Druid gets 4 specs (Balance, Feral, Guardian, Restoration)
            # Rogue still "Combat" (not yet Outlaw)
        },
        "class_roles": {
            # DK: only Blood can tank now
        },
        "raids": [...],  # BWD, BoT, TotFW, Firelands, DS, etc.
    },
    "mop": {
        "display_name": "Mists of Pandaria",
        "version": "5.x",
        "classes": [..., "Monk"],  # Monk added
        "class_specs": {
            "Monk": ["Brewmaster", "Mistweaver", "Windwalker"],
            ...
        },
        "class_roles": {
            "Monk": ["main_tank", "off_tank", "healer", "melee_dps"],
            ...
        },
        "raids": [...],
    },
    "wod": {
        "display_name": "Warlords of Draenor",
        "version": "6.x",
        # Same classes as MoP
    },
    "legion": {
        "display_name": "Legion",
        "version": "7.x",
        "classes": [..., "Demon Hunter"],  # DH added
        "class_specs": {
            "Demon Hunter": ["Havoc", "Vengeance"],
            "Rogue": ["Assassination", "Outlaw", "Subtlety"],  # Combat → Outlaw
            "Hunter": ["Beast Mastery", "Marksmanship", "Survival"],  # Survival now melee
            ...
        },
        "class_roles": {
            "Demon Hunter": ["main_tank", "off_tank", "melee_dps"],
            "Hunter": ["range_dps", "melee_dps"],  # Survival is melee now
            ...
        },
        "raids": [...],
    },
    "dragonflight": {
        "display_name": "Dragonflight",
        "version": "10.x",
        "classes": [..., "Evoker"],  # Evoker added
        "class_specs": {
            "Evoker": ["Devastation", "Preservation", "Augmentation"],
            ...
        },
        "class_roles": {
            "Evoker": ["range_dps", "healer"],
            ...
        },
        "raids": [...],
    },
}
```

#### 4.4.2 Guild → Expansion Binding

Each guild selects which expansion(s)/addon(s) it plays:

```python
class GuildExpansion(db.Model):
    """Which expansions a guild has enabled."""
    __tablename__ = "guild_expansions"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    expansion_key = Column(String(30), nullable=False)  # e.g., "wotlk"
    is_primary = Column(Boolean, default=False)          # Main expansion
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("guild_id", "expansion_key"),
    )
```

**How it works:**
1. Guild admin creates guild → selects primary expansion (e.g., "wotlk")
2. Optionally enables additional expansions (e.g., for alt raids on different servers)
3. Character creation form filters available classes based on guild's expansion(s)
4. Raid definitions filter based on guild's expansion(s)
5. Class→Role matrix served via `/api/v1/meta/constants` is expansion-aware

#### 4.4.3 Dynamic Constants API

The existing `/api/v1/meta/constants` endpoint should become expansion-aware:

```
GET /api/v1/meta/constants?expansion=wotlk

Response:
{
    "expansion": "wotlk",
    "wow_classes": ["Warrior", "Paladin", ..., "Death Knight"],
    "class_specs": { ... },
    "class_roles": { ... },
    "raids": [ ... ],
    "roles": [ ... ]  // Same across all expansions
}
```

For guilds with multiple expansions enabled:
```
GET /api/v1/guilds/{guild_id}/constants

Response:
{
    "primary_expansion": "wotlk",
    "enabled_expansions": ["wotlk", "tbc"],
    "merged_classes": ["Warrior", ..., "Death Knight"],  // Union of all enabled
    "class_availability": {
        "Death Knight": ["wotlk"],       // Only in WotLK
        "Warrior": ["wotlk", "tbc"],     // In both
        ...
    },
    ...
}
```

---

## 5. Class → Role Ability Matrix for Guild Admins

### 5.1 Purpose

Guild admins need a clear, visual matrix showing which classes can fill which
raid roles. This matrix:
- Is **read-only by default** (derived from expansion data)
- Can be **customized per guild** (guild admin can restrict/allow specific class-role combos)
- Drives character creation and signup validation

### 5.2 Default Matrix (WotLK Example)

| Class | Main Tank | Off Tank | Melee DPS | Ranged DPS | Healer |
|-------|:---------:|:--------:|:---------:|:----------:|:------:|
| Death Knight | ✅ | ✅ | ✅ | ❌ | ❌ |
| Druid | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hunter | ❌ | ❌ | ❌ | ✅ | ❌ |
| Mage | ❌ | ❌ | ❌ | ✅ | ❌ |
| Paladin | ✅ | ✅ | ✅ | ❌ | ✅ |
| Priest | ❌ | ❌ | ❌ | ✅ | ✅ |
| Rogue | ❌ | ❌ | ✅ | ❌ | ❌ |
| Shaman | ❌ | ❌ | ✅ | ✅ | ✅ |
| Warlock | ❌ | ❌ | ❌ | ✅ | ❌ |
| Warrior | ✅ | ✅ | ✅ | ❌ | ❌ |

### 5.3 Guild Admin Customization

Guild admins should be able to override the default matrix for their guild.
Use cases:
- A hardcore guild may restrict Paladin from Main Tank role
- A casual guild may allow any class to fill any role for fun events
- A progression guild may have different matrix for heroic vs. normal raids

#### 5.3.1 Override Model

```python
class GuildClassRoleOverride(db.Model):
    """Per-guild customization of class → role assignments."""
    __tablename__ = "guild_class_role_overrides"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    class_name = Column(String(30), nullable=False)    # "Death Knight"
    role = Column(String(20), nullable=False)           # "main_tank"
    allowed = Column(Boolean, nullable=False)           # True = allow, False = restrict

    __table_args__ = (
        UniqueConstraint("guild_id", "class_name", "role"),
    )
```

**Resolution logic:**
1. Start with expansion default matrix
2. Apply guild-level overrides (if any)
3. Result = effective matrix for that guild

#### 5.3.2 Admin UI Component

New component in guild settings: **Class-Role Matrix Editor**

```
┌─────────────────────────────────────────────────────────────┐
│  Class-Role Matrix                          [Reset Defaults] │
│                                                              │
│  ┌─────────────┬───────┬───────┬───────┬───────┬───────┐    │
│  │ Class       │  MT   │  OT   │ Melee │ Range │ Heal  │    │
│  ├─────────────┼───────┼───────┼───────┼───────┼───────┤    │
│  │ Death Knight│  [✓]  │  [✓]  │  [✓]  │  [ ]  │  [ ]  │    │
│  │ Druid       │  [✓]  │  [✓]  │  [✓]  │  [✓]  │  [✓]  │    │
│  │ Hunter      │  [ ]  │  [ ]  │  [ ]  │  [✓]  │  [ ]  │    │
│  │ ...         │       │       │       │       │       │    │
│  └─────────────┴───────┴───────┴───────┴───────┴───────┘    │
│                                                              │
│  ⓘ Checked = class can sign up for this role                │
│  ⚠ Overridden cells highlighted in yellow                    │
│                                              [Save Changes]  │
└──────────────────────────────────────────────────────────────┘
```

### 5.4 Matrix Enforcement Points

The class-role matrix should be enforced at:

1. **Character creation** — Only allow roles valid for the character's class
2. **Signup creation** — Validate that the character's role is allowed in the matrix
3. **Lineup assignment** — Prevent placing a character in a disallowed role slot
4. **Constants API** — Return guild-specific matrix so frontend can filter UI options

### 5.5 New API Endpoints

```
GET  /api/v1/guilds/{guild_id}/class-role-matrix
     → Returns effective matrix (defaults + overrides)

PUT  /api/v1/guilds/{guild_id}/class-role-matrix
     → Bulk update overrides (guild_admin permission required)

DELETE /api/v1/guilds/{guild_id}/class-role-matrix
     → Reset to expansion defaults (guild_admin permission required)
```

---

## 6. Plugin Architecture

### 6.1 Plugin Registration Pattern

Create a lightweight plugin system that allows expansion packs and integrations
to register themselves without modifying core code.

```python
# app/plugins/__init__.py

class PluginRegistry:
    """Central registry for pluggable features."""

    _plugins: dict[str, 'BasePlugin'] = {}

    @classmethod
    def register(cls, plugin: 'BasePlugin') -> None:
        cls._plugins[plugin.key] = plugin

    @classmethod
    def get(cls, key: str) -> 'BasePlugin | None':
        return cls._plugins.get(key)

    @classmethod
    def all(cls) -> dict[str, 'BasePlugin']:
        return dict(cls._plugins)


class BasePlugin:
    """Base class for all plugins."""
    key: str                    # Unique identifier
    display_name: str           # Human-readable name
    version: str               # Plugin version
    dependencies: list[str]    # Other plugin keys this depends on

    def register_blueprints(self, app) -> None:
        """Register API blueprints with the Flask app."""
        pass

    def register_models(self) -> list:
        """Return list of SQLAlchemy models this plugin provides."""
        return []

    def get_feature_flags(self) -> dict[str, bool]:
        """Return default feature flag states for this plugin."""
        return {}

    def on_guild_enable(self, guild_id: int) -> None:
        """Called when a guild enables this plugin."""
        pass

    def on_guild_disable(self, guild_id: int) -> None:
        """Called when a guild disables this plugin."""
        pass
```

### 6.2 Expansion Pack Plugin Example

```python
# app/plugins/expansions/wotlk.py

class WotlkExpansion(BasePlugin):
    key = "wotlk"
    display_name = "Wrath of the Lich King"
    version = "3.3.5"
    dependencies = []

    def get_classes(self) -> list[str]:
        return ["Warrior", "Paladin", "Hunter", "Rogue", "Priest",
                "Shaman", "Mage", "Warlock", "Druid", "Death Knight"]

    def get_class_specs(self) -> dict[str, list[str]]:
        return {
            "Death Knight": ["Blood", "Frost", "Unholy"],
            "Druid": ["Balance", "Feral Combat", "Restoration"],
            # ... current CLASS_SPECS
        }

    def get_class_roles(self) -> dict[str, list[str]]:
        return {
            "Death Knight": ["main_tank", "off_tank", "melee_dps"],
            # ... current CLASS_ROLES
        }

    def get_raids(self) -> list[dict]:
        return [
            # ... current WOTLK_RAIDS
        ]

    def get_armory_providers(self) -> list[str]:
        return ["warmane"]  # Available armory providers for this expansion
```

### 6.3 Integration Plugin Example

```python
# app/plugins/integrations/warmane.py

class WarmaneIntegration(BasePlugin):
    key = "warmane"
    display_name = "Warmane Integration"
    version = "1.0.0"
    dependencies = ["wotlk"]

    def register_blueprints(self, app):
        from app.api.v1.warmane import warmane_bp
        from app.api.v1.armory import armory_bp
        app.register_blueprint(warmane_bp, url_prefix="/api/v1/warmane")
        app.register_blueprint(armory_bp, url_prefix="/api/v1/guilds/<int:guild_id>/armory")

    def get_feature_flags(self):
        return {
            "character_sync": True,
            "armory_integration": True,
        }
```

### 6.4 Frontend Plugin Support

The frontend should dynamically load components based on enabled plugins:

```javascript
// src/plugins/registry.js

export const pluginRegistry = {
  expansions: {},   // Registered expansion definitions
  components: {},   // Plugin-provided Vue components
  routes: [],       // Plugin-provided routes

  register(plugin) {
    if (plugin.type === 'expansion') {
      this.expansions[plugin.key] = plugin
    }
    if (plugin.components) {
      Object.assign(this.components, plugin.components)
    }
    if (plugin.routes) {
      this.routes.push(...plugin.routes)
    }
  }
}
```

---

## 7. Phased Implementation Roadmap

### Phase 1: Foundation Decoupling (No Breaking Changes)
**Goal:** Restructure internals without changing any external behavior.

- [ ] Create `app/expansions/` directory with expansion registry
- [ ] Move `CLASS_ROLES`, `CLASS_SPECS`, `WOTLK_RAIDS` from `constants.py` into expansion-specific config files
- [ ] Keep backward compatibility: `constants.py` imports from `app/expansions/wotlk.py`
- [ ] Add `expansion` field to Guild model (default: `"wotlk"`)
- [ ] Make `meta.py` constants endpoint expansion-aware (with backward-compatible default)
- [ ] Add expansion-aware validation in character service
- [ ] All existing tests must pass unchanged

### Phase 2: Guild Membership Hardening
**Goal:** Give guild admins control over membership.

- [ ] Add `GuildVisibility` enum and `visibility` field to Guild model
- [ ] Add `GuildInvitation` model
- [ ] Extend `MemberStatus` with `APPLIED` and `DECLINED`
- [ ] Create invitation endpoints (send, accept, decline, list)
- [ ] Create application endpoints (apply, approve, decline)
- [ ] Add `invite_members` and `approve_applications` permissions
- [ ] Update guild list endpoint to respect visibility settings
- [ ] Change `allow_self_join` default to `False`
- [ ] Build invitation management UI (guild admin panel)
- [ ] Add guild discovery page (public/listed guilds only)

### Phase 3: Class-Role Matrix
**Goal:** Give guild admins a visual matrix to control class-role assignments.

- [ ] Create `GuildClassRoleOverride` model
- [ ] Create matrix API endpoints (GET/PUT/DELETE)
- [ ] Add matrix resolution logic (defaults + overrides)
- [ ] Build matrix editor UI component
- [ ] Integrate matrix checks into character creation
- [ ] Integrate matrix checks into signup validation
- [ ] Integrate matrix checks into lineup assignment
- [ ] Add `manage_class_role_matrix` permission

### Phase 4: Multi-Expansion Support
**Goal:** Support guilds running different WoW expansions.

- [ ] Create `GuildExpansion` model (guild ↔ expansion binding)
- [ ] Define expansion packs: Classic, TBC, WotLK, Cata, MoP, WoD, Legion, BfA, SL, DF, TWW
- [ ] Add class/spec/role definitions for each expansion
- [ ] Add raid definitions for each expansion
- [ ] Create expansion selection flow in guild creation
- [ ] Update character creation to filter classes by guild expansion
- [ ] Update raid definition seeder for multi-expansion
- [ ] Update frontend constants store for expansion-awareness
- [ ] Add expansion selector in guild settings

### Phase 5: Plugin Architecture
**Goal:** Make features truly pluggable.

- [ ] Create `app/plugins/` framework (BasePlugin, PluginRegistry)
- [ ] Refactor Warmane integration into a plugin
- [ ] Refactor Discord integration into a plugin
- [ ] Create plugin enable/disable API
- [ ] Build plugin management UI (guild settings)
- [ ] Create plugin developer documentation
- [ ] Frontend dynamic component loading for plugins

### Phase 6: SaaS Infrastructure
**Goal:** Add billing and organization management.

- [ ] Evaluate need for row-level tenancy (guild_id enforcement)
- [ ] Add subscription/billing model (if needed)
- [ ] Add usage tracking per guild
- [ ] Add API rate limiting per guild
- [ ] Add data export/import for guild portability
- [ ] Add guild deletion with data cleanup

---

## 8. Migration & Backward Compatibility

### 8.1 Database Migration Strategy

All schema changes should use incremental migrations (Alembic or Flask-Migrate):

1. **Add new columns with defaults** — existing rows get sensible defaults
2. **Never remove columns in the same release** — deprecate first
3. **Data migrations** — populate new fields from existing data
4. **Feature flags** — new features start disabled by default

### 8.2 API Versioning

Current API is `/api/v1/`. Strategy:

- **v1 stays backward compatible** — no breaking changes
- **New endpoints** added to v1 with new prefixes
- **v2** only when breaking changes are necessary (Phase 5+)

### 8.3 Frontend Compatibility

- Constants store should gracefully handle missing expansion data
- Components should use optional chaining for new fields
- New UI features should be behind feature flag checks

---

## 9. Open Questions & Decisions

### 9.1 Decisions Needed

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Where to store expansion definitions? | Python dicts / JSON files / DB tables | **Python dicts** (fast, type-safe, version-controlled) with DB-level overrides |
| 2 | Should guilds support multiple expansions simultaneously? | Single / Multiple | **Single primary** with optional multi-expansion for alt raids |
| 3 | How to handle spec changes across expansions? | Single enum / Expansion-keyed map | **Expansion-keyed map** (specs differ too much between expansions) |
| 4 | Should class-role matrix overrides be per-raid or per-guild? | Per-raid / Per-guild / Both | **Per-guild first**, per-raid as Phase 3 extension |
| 5 | Invitation expiry default? | 24h / 7d / 30d / Never | **7 days** with guild admin override |
| 6 | Allow users to see guilds they're not members of? | Yes (listed) / No (private) | **Configurable** per guild (visibility setting) |
| 7 | Database name change from `wotlk_calendar.db`? | Yes / No | **Yes** — rename to `raid_calendar.db` or `guild_calendar.db` in a future phase |
| 8 | Should the `WowClass` Python enum remain? | Keep as universal / Replace with expansion-dynamic | **Keep as superset** of all classes; filter at runtime by expansion |
| 9 | Should the default expansion be a named constant? | Hardcoded / Constant | **Named constant** (`DEFAULT_EXPANSION = "wotlk"`) to avoid scattered magic strings |

### 9.2 Research Items

- [ ] Survey private server APIs (TrinityCore, AzerothCore, CMaNGOS) for armory integration possibilities
- [ ] Investigate retail WoW Blizzard API for character/guild data access
- [ ] Evaluate whether Monk/DH/Evoker specs need additional Role enum values (e.g., "support" for Augmentation Evoker)
- [ ] Research demand for non-WoW game support (FFXIV, ESO) — affects how generic the plugin system should be

### 9.3 Technical Debt to Address First

Before starting Phase 1, complete these from the existing cleanup plan:
- [ ] Consolidate frontend role label maps (7 duplicates)
- [ ] Consolidate CLASS_ROLES/CLASS_SPECS between frontend and backend
- [ ] Add service layers for modules that access DB directly (raid_definitions, templates, series, roles)

---

## Appendix A: Full Expansion Spec Reference

### Classic / TBC (9 classes, 27 specs)
```
Warrior:    Arms, Fury, Protection
Paladin:    Holy, Protection, Retribution
Hunter:     Beast Mastery, Marksmanship, Survival
Rogue:      Assassination, Combat, Subtlety
Priest:     Discipline, Holy, Shadow
Shaman:     Elemental, Enhancement, Restoration
Mage:       Arcane, Fire, Frost
Warlock:    Affliction, Demonology, Destruction
Druid:      Balance, Feral Combat, Restoration
```

### WotLK (10 classes, 30 specs)
```
+ Death Knight: Blood, Frost, Unholy
(all other classes same as Classic/TBC)
```

### Cataclysm / MoP (11-12 classes, 34-37 specs)
```
Druid:      Balance, Feral, Guardian, Restoration  (4 specs; "Feral Combat" split)
Rogue:      Assassination, Combat, Subtlety
+ Monk:     Brewmaster, Mistweaver, Windwalker     (MoP only)
(Death Knight: Blood=tank only, Frost/Unholy=DPS only)
```

### WoD (12 classes, 37 specs)
```
(same as MoP)
```

### Legion / BfA / Shadowlands (13 classes, 39 specs)
```
Rogue:      Assassination, Outlaw, Subtlety        ("Combat" → "Outlaw")
Hunter:     Beast Mastery, Marksmanship, Survival   (Survival = melee)
+ Demon Hunter: Havoc, Vengeance
```

### Dragonflight / The War Within (14 classes, 42 specs)
```
+ Evoker:   Devastation, Preservation, Augmentation
```

---

## Appendix B: Permission Matrix (Current + Proposed)

### Current Permissions (43)

| Category | Permissions |
|----------|------------|
| Events (7) | view_events, create_events, edit_events, delete_events, lock_signups, cancel_events, duplicate_events |
| Signups (8) | sign_up, view_signups, delete_own_signup, decline_own_signup, manage_signups, ban_characters, unban_characters, request_replacement |
| Lineup (3) | update_lineup, confirm_lineup, reorder_bench |
| Characters (2) | manage_own_characters, view_member_characters |
| Attendance (2) | view_attendance, record_attendance |
| Definitions (4) | manage_raid_definitions, manage_default_definitions, manage_templates, manage_series |
| Guild (7) | create_guild, view_guild, update_guild_settings, delete_guild, add_members, remove_members, update_member_roles, manage_guild_roles |
| Notifications (1) | view_notifications |
| Admin (6) | list_system_users, manage_system_users, trigger_sync, manage_autosync, manage_roles, manage_system_settings |

### Proposed New Permissions

| Category | Permission | Description |
|----------|-----------|-------------|
| Guild | invite_members | Send guild invitations |
| Guild | approve_applications | Approve/decline membership applications |
| Guild | manage_guild_visibility | Change guild visibility settings |
| Guild | manage_class_role_matrix | Edit class-role assignment matrix |
| Guild | manage_guild_expansions | Enable/disable expansion packs for guild |
| Admin | manage_plugins | Enable/disable system plugins |
