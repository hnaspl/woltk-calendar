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
10. [Phase 0: Row-Level Tenancy (guild_id) — Detailed Plan](#10-phase-0-row-level-tenancy-guild_id--detailed-plan)

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
admins control while keeping the flexibility WoW players need.

> **Update:** After further analysis, we recommend implementing **Row-level
> tenancy (`tenant_id` / `guild_id` on every table)** as **Phase 0** — before
> any other feature work. The rationale and full detailed plan are in
> [Section 10: Phase 0](#10-phase-0-row-level-tenancy-guild_id--detailed-plan).
> This ensures every subsequent phase (invitation system, multi-expansion,
> plugins, SaaS billing) is built on a solid tenant-isolated foundation, rather
> than having to retrofit tenant checks into an already-complex codebase.

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

### Phase 0: Row-Level Tenancy (`guild_id` on every table)
**Goal:** Remodel the entire application to enforce row-level tenant isolation
(`guild_id` on every guild-scoped table) **before** any feature work.

> **This phase is a prerequisite for all other phases.** See
> [Section 10](#10-phase-0-row-level-tenancy-guild_id--detailed-plan) for the
> complete table-by-table, query-by-query, file-by-file change plan.

- [ ] Add `guild_id` FK to tables that lack it (Signup, LineupSlot, RaidBan, AttendanceRecord, CharacterReplacement)
- [ ] Data migration: backfill `guild_id` from parent relationships
- [ ] Add composite indexes on `(guild_id, ...)` for all tenant-scoped tables
- [ ] Update every service-layer query to include `guild_id` filter
- [ ] Update every API route to pass `guild_id` through the call chain
- [ ] Add `TenantMixin` or `@filter_by_tenant` decorator for query safety
- [ ] Add tests verifying cross-tenant data isolation
- [ ] Regression-test all 632+ existing tests

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

- [x] ~~Evaluate need for row-level tenancy (guild_id enforcement)~~ → **Moved to Phase 0**
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

---

## 10. Phase 0: Row-Level Tenancy (`guild_id`) — Detailed Plan

> **Priority:** This is the very first implementation step — before Phase 1
> (expansion registry), Phase 2 (invitations), or any other feature work.
>
> **Why first?** Every subsequent phase adds more tables, queries, and features.
> If we retrofit `guild_id` enforcement later, we must audit every new query
> written by Phases 1-6. Doing it now means all future code is written with
> tenant isolation baked in from day one, and debugging cross-tenant data leaks
> in a mature codebase is exponentially harder.

---

### 10.1 What Is Row-Level Tenancy?

Row-level tenancy (also called "shared database, shared schema" multi-tenancy)
means **every guild-scoped row** in the database carries a `guild_id` foreign
key that identifies which tenant (guild) owns that data. Every query that reads
or writes guild-scoped data **must** include a `WHERE guild_id = :guild_id`
filter.

```
┌─────────────────────────────────────────────────────────┐
│                    Single Database                       │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Guild A rows  │  │ Guild B rows  │  │ Guild C rows  │  │
│  │ guild_id = 1  │  │ guild_id = 2  │  │ guild_id = 3  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  Isolation enforced by WHERE guild_id = ? on EVERY query │
└─────────────────────────────────────────────────────────┘
```

### 10.2 Risks & Mitigation

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| 1 | **Cross-tenant data leak** — forgetting `guild_id` filter on a query exposes Guild A's data to Guild B | 🔴 Critical | High (many queries) | `TenantMixin` base class with `@validates` + integration tests per endpoint |
| 2 | **Data migration corruption** — backfilling `guild_id` on existing rows uses wrong parent chain | 🔴 Critical | Medium | Run migration on a copy first; write verification queries; compare row counts |
| 3 | **Performance regression** — adding `guild_id` column + index to every table increases write amplification | 🟡 Medium | Low | Composite indexes `(guild_id, <existing_index>)` replace single-column indexes; SQLite/Postgres handle this well |
| 4 | **Broken unique constraints** — existing `UNIQUE(raid_event_id, character_id)` may need to become `UNIQUE(guild_id, raid_event_id, character_id)` | 🟡 Medium | Medium | Audit every constraint; some stay event-scoped (event already belongs to one guild) |
| 5 | **ORM relationship breakage** — adding `guild_id` to child tables may confuse existing `relationship()` declarations | 🟡 Medium | Low | Relationships are FK-based, not column-based; adding a column doesn't break them |
| 6 | **Test suite breakage** — all 632+ tests assume current schema | 🟡 Medium | High | Run full suite after each table migration; fix tests incrementally |
| 7 | **Global admin queries break** — admin dashboard counts (`SELECT COUNT(*) FROM users`) should NOT be tenant-filtered | 🟡 Medium | Medium | Clearly separate global-scoped tables/queries from tenant-scoped ones (see §10.3) |
| 8 | **Seed data duplication** — system-wide seeds (permissions, roles, default raid definitions) must remain `guild_id=NULL` | 🟢 Low | Low | Only guild-scoped tables get `NOT NULL` constraint; system tables keep `guild_id` nullable or absent |
| 9 | **Frontend breaks** — API response shape changes if we add `guild_id` to `to_dict()` output | 🟢 Low | Low | `guild_id` already present in most `to_dict()` outputs; add to new ones consistently |
| 10 | **Alembic migration ordering** — tables with FK dependencies must be migrated in correct order | 🟡 Medium | Medium | Single migration file; backfill in parent→child order |

### 10.3 Table Classification: Global vs. Tenant-Scoped

Every table in the application falls into one of three categories:

| Category | Tables | `guild_id` needed? | Rationale |
|----------|--------|-------------------|-----------|
| **Global (system-wide)** | `users`, `system_settings`, `permissions`, `system_roles`, `role_permissions`, `role_grant_rules`, `job_queue` | ❌ No | These are shared across all tenants. Users can belong to multiple guilds. Permissions/roles are system-wide definitions. |
| **Already tenant-scoped** | `guilds`, `guild_memberships`, `guild_features`, `characters`, `raid_definitions`, `raid_templates`, `event_series`, `raid_events`, `notifications` | ✅ Already have `guild_id` | These tables already carry `guild_id` as a direct column. |
| **Needs `guild_id` added** | `signups`, `lineup_slots`, `raid_bans`, `attendance_records`, `character_replacements`, `armory_configs` | ⚠️ **Must add** | These tables are implicitly tenant-scoped via parent FK chains (e.g., `signup → raid_event → guild`), but lack a direct `guild_id` column for efficient filtering and safety. |

### 10.4 Table-by-Table Change Plan

#### 10.4.1 Tables That Already Have `guild_id` (Verify & Harden)

These tables already have `guild_id`. The work here is to **verify** that every
query on them includes a `guild_id` filter and to add a composite index if
missing.

##### `guilds` (no changes needed)
- `guild_id` is the PK itself (`id`); this IS the tenant table.
- No filter needed — this table defines tenants.

##### `guild_memberships`
- **Has:** `guild_id` FK → `guilds.id` ✅
- **Has:** Unique constraint `(guild_id, user_id)` ✅
- **Action:** Verify all queries filter by `guild_id`. Already done in `guild_service.py`, `permissions.py`, `api_helpers.py`.
- **Risk:** None — already properly scoped.

##### `guild_features`
- **Has:** `guild_id` FK → `guilds.id` ✅
- **Has:** Unique constraint `(guild_id, feature_key)` ✅
- **Action:** No changes needed. `feature_service.py` already filters by `guild_id`.

##### `characters`
- **Has:** `guild_id` FK → `guilds.id` ✅
- **Has:** Unique constraint `(realm_name, name, guild_id)` ✅
- **Action:** Verify `character_service.py` queries always include `guild_id`. Current `list_characters()` (line 147) already filters by `guild_id`. `get_character()` (line 59) uses `db.session.get()` by PK — **should add `guild_id` ownership check after fetch**.

| File | Function | Line | Current | Change needed |
|------|----------|------|---------|---------------|
| `character_service.py` | `get_character()` | 59 | `db.session.get(Character, character_id)` | Add `if char and char.guild_id != guild_id: return None` after fetch |
| `character_service.py` | `delete_character()` | ~80 | Deletes by object | Caller must verify `guild_id` match (already done in API layer) |
| `character_service.py` | `archive_character()` | ~128 | Updates by object | Caller must verify `guild_id` match (already done in API layer) |

##### `raid_definitions`
- **Has:** `guild_id` FK → `guilds.id` (nullable — `NULL` = builtin/default) ✅
- **Action:** Keep nullable. `guild_id=NULL` means system-wide default definitions. `raid_service.py` already filters by `guild_id` or `guild_id.is_(None)`.

##### `raid_templates`
- **Has:** `guild_id` FK → `guilds.id` ✅
- **Action:** Verify `event_service.py` `list_templates()` (line 63) already filters by `guild_id`. ✅

##### `event_series`
- **Has:** `guild_id` FK → `guilds.id` ✅
- **Action:** Verify `event_service.py` `list_series()` (line 152) already filters by `guild_id`. ✅

##### `raid_events`
- **Has:** `guild_id` FK → `guilds.id`, indexed ✅
- **Has:** Composite index `(guild_id, starts_at_utc)` ✅
- **Action:** Verify all event queries include `guild_id`. `event_service.py` `list_events()` and variants already filter by `guild_id`. ✅

##### `notifications`
- **Has:** `guild_id` FK → `guilds.id` (nullable) ✅
- **Action:** Keep nullable — some notifications are system-wide (not guild-specific). `notification_service.py` queries by `user_id`, not by `guild_id` — this is correct because notifications are user-scoped with optional guild context.

#### 10.4.2 Tables That Need `guild_id` Added

These are the **critical changes**. Each table below currently relies on a FK
chain to determine tenant ownership (e.g., `signup.raid_event_id → raid_events.guild_id`).
Adding a direct `guild_id` column allows:
1. Direct tenant-scoped queries without JOINs
2. Safety — even if a bug corrupts a parent FK, the tenant boundary holds
3. Future index optimization

---

##### `signups` — Add `guild_id`

**Current state:** Tenant is inferred via `signup.raid_event_id → raid_events.guild_id`.

**Model change (`app/models/signup.py`):**
```python
# Add to Signup class (after user_id):
guild_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True
)

# Add relationship:
guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
```

**Index changes:**
```python
# Update __table_args__:
# Note: The single-column ix_signups_guild index serves queries that filter
# only by guild_id (e.g., "all signups for this guild"). The composite
# ix_signups_guild_event index serves the more common query pattern that
# filters by guild_id + raid_event_id together. The composite index can also
# satisfy guild_id-only queries (leftmost prefix), so the single-column index
# is optional — include it only if the DB engine (SQLite) doesn't efficiently
# use leftmost prefix scans. Can be dropped after benchmarking.
__table_args__ = (
    sa.UniqueConstraint("raid_event_id", "character_id", name="uq_event_character"),
    sa.Index("ix_signups_raid_event", "raid_event_id"),
    sa.Index("ix_signups_user", "user_id"),
    sa.Index("ix_signups_guild", "guild_id"),            # NEW — guild-only lookups
    sa.Index("ix_signups_guild_event", "guild_id", "raid_event_id"),  # NEW composite
)
```

**Unique constraint note:** The existing `uq_event_character` constraint
`(raid_event_id, character_id)` does **not** need `guild_id` added — an event
already belongs to exactly one guild, so the constraint is implicitly
guild-scoped.

**Data migration (SQL):**
```sql
-- Backfill guild_id from parent raid_events
UPDATE signups
SET guild_id = (
    SELECT raid_events.guild_id
    FROM raid_events
    WHERE raid_events.id = signups.raid_event_id
);
```

**Queries to update in `signup_service.py`:**

| Function | Line(s) | Current query | Change |
|----------|---------|---------------|--------|
| `create_signup()` | 259 | `db.session.add(signup)` | Set `signup.guild_id = guild_id` before adding |
| `get_signup()` | 272 | `db.session.get(Signup, signup_id)` | Add `guild_id` ownership check after fetch |
| `update_signup()` | 291 | Update by object | Caller verifies guild_id (via event ownership check) |
| `delete_signup()` | 315 | Delete by object | Caller verifies guild_id (via event ownership check) |
| `list_signups()` | 344-349 | `Signup.raid_event_id == event_id` | Add `.where(Signup.guild_id == guild_id)` |
| `list_user_signups()` | 354-362 | Filters by user_id and event list | Add `.where(Signup.guild_id == guild_id)` |
| `list_user_characters_for_event()` | 582-588 | `Character.guild_id == guild_id` | Already scoped via character; also add to signup subquery |

**Queries to update in API layer (`app/api/v1/signups.py`):**

| Function | Line | Change |
|----------|------|--------|
| `list_signups()` | 28 | Pass `guild_id` to `build_guild_role_map()` — already done ✅ |
| `create_signup()` | various | Pass `guild_id` from event context to `signup_service.create_signup()` |

---

##### `lineup_slots` — Add `guild_id`

**Current state:** Tenant is inferred via `lineup_slot.raid_event_id → raid_events.guild_id`.

**Model change (`app/models/signup.py`):**
```python
# Add to LineupSlot class (after raid_event_id):
guild_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True
)

guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
```

**Index changes:**
```python
__table_args__ = (
    sa.UniqueConstraint("raid_event_id", "slot_group", "slot_index", name="uq_event_slot"),
    sa.Index("ix_lineup_slots_raid_event", "raid_event_id"),
    sa.Index("ix_lineup_slots_signup", "signup_id"),
    sa.Index("ix_lineup_slots_guild", "guild_id"),                     # NEW
    sa.Index("ix_lineup_slots_guild_event", "guild_id", "raid_event_id"),  # NEW composite
)
```

**Data migration (SQL):**
```sql
UPDATE lineup_slots
SET guild_id = (
    SELECT raid_events.guild_id
    FROM raid_events
    WHERE raid_events.id = lineup_slots.raid_event_id
);
```

**Queries to update in `lineup_service.py`:**

| Function | Line(s) | Current query | Change |
|----------|---------|---------------|--------|
| `get_lineup()` | 18-26 | `LineupSlot.raid_event_id == event_id` | Add `.where(LineupSlot.guild_id == guild_id)` |
| `add_slot()` | 60-81 | Max slot_index query + add | Set `slot.guild_id = guild_id`; add `guild_id` to max query |
| `remove_slot()` | 86-89 | Delete by event_id + signup_id | Add `LineupSlot.guild_id == guild_id` |
| `count_role_slots()` | 94-99 | Count by event_id + group | Add `LineupSlot.guild_id == guild_id` |
| `get_bench_slot()` | 109-114 | Query by event_id + signup_id + bench | Add `LineupSlot.guild_id == guild_id` |
| `get_bench_position()` | 124-133 | Count by event + group + index | Add `guild_id` filter |
| `update_slot_group()` | 145-153 | Update by event + signup | Add `guild_id` filter |
| `upsert_slot()` | 164-184 | Query + insert/update | Add `guild_id` to query and new slot |
| `save_full_lineup()` | 225-397 | Complex batch operation | Set `guild_id` on every new `LineupSlot`; add filter on delete query (line 237) |
| `reorder_bench()` | 463-512 | Query + update bench slots | Add `guild_id` filter to all queries |
| `confirm_lineup()` | 541-546 | Update confirmed_at | `guild_id` added via `get_lineup()` |
| `add_to_bench_queue()` | 560-561 | Insert bench slot | Set `slot.guild_id = guild_id` |

---

##### `raid_bans` — Add `guild_id`

**Current state:** Tenant is inferred via `raid_ban.raid_event_id → raid_events.guild_id`.

**Model change (`app/models/signup.py`):**
```python
# Add to RaidBan class (after raid_event_id):
guild_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True
)

guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
```

**Data migration (SQL):**
```sql
UPDATE raid_bans
SET guild_id = (
    SELECT raid_events.guild_id
    FROM raid_events
    WHERE raid_events.id = raid_bans.raid_event_id
);
```

**Queries to update in `signup_service.py`:**

| Function | Line(s) | Change |
|----------|---------|--------|
| `get_ban()` | 371-376 | Add `.where(RaidBan.guild_id == guild_id)` |
| `list_bans()` | 382-387 | Add `.where(RaidBan.guild_id == guild_id)` |
| `create_ban()` | 403 | Set `ban.guild_id = guild_id` before `db.session.add()` |
| `delete_ban()` | 413 | Verify `ban.guild_id == guild_id` before delete |

---

##### `attendance_records` — Add `guild_id`

**Current state:** Tenant is inferred via `attendance.raid_event_id → raid_events.guild_id`.

**Model change (`app/models/attendance.py`):**
```python
# Add to AttendanceRecord class (after raid_event_id):
guild_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True
)

guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
```

**Unique constraint update:**
```python
# Current: uq_attendance_event_user (raid_event_id, user_id)
# Keep as-is — event_id is already guild-scoped, so adding guild_id to the
# unique constraint is redundant (an event can only belong to one guild).
```

**Data migration (SQL):**
```sql
UPDATE attendance_records
SET guild_id = (
    SELECT raid_events.guild_id
    FROM raid_events
    WHERE raid_events.id = attendance_records.raid_event_id
);
```

**Queries to update in `attendance_service.py`:**

| Function | Line(s) | Change |
|----------|---------|--------|
| `record_attendance()` | 23-28, 46 | Add `guild_id` to the `WHERE` clause and set on new record |
| `get_event_attendance()` | 53-57 | Add `.where(AttendanceRecord.guild_id == guild_id)` |
| `get_character_history()` | 68-80 | Add `.where(AttendanceRecord.guild_id == guild_id)` or leave cross-guild if intentional |

**Queries to update in API layer (`app/api/v1/attendance.py`):**

| Function | Line(s) | Change |
|----------|---------|--------|
| `record_or_update()` | 25-32 | Pass `guild_id` from route to service |
| `get_attendance()` | 53-58 | Pass `guild_id` to lineup slot check |

---

##### `character_replacements` — Add `guild_id`

**Current state:** Tenant is inferred via `replacement.signup_id → signups.raid_event_id → raid_events.guild_id` (2-hop chain).

**Model change (`app/models/signup.py`):**
```python
# Add to CharacterReplacement class (after signup_id):
guild_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True
)

guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
```

**Data migration (SQL):**
```sql
UPDATE character_replacements
SET guild_id = (
    SELECT raid_events.guild_id
    FROM signups
    JOIN raid_events ON raid_events.id = signups.raid_event_id
    WHERE signups.id = character_replacements.signup_id
);
```

**Queries to update in `signup_service.py`:**

| Function | Line(s) | Change |
|----------|---------|--------|
| `request_replacement()` | 436-455 | Add `guild_id` filter to existing-check query; set `req.guild_id = guild_id` |
| `get_pending_replacement()` | 461-472 | Add `.where(CharacterReplacement.guild_id == guild_id)` |
| `list_pending_replacements()` | 478-493 | Add `.where(CharacterReplacement.guild_id == guild_id)` |
| `confirm_replacement()` | 522-570 | Add `guild_id` filter to conflict and cleanup queries |

---

##### `armory_configs` — Evaluate

**Current state:** `armory_configs` has `user_id` FK but no `guild_id`.

**Decision:** `armory_configs` is **user-scoped**, not guild-scoped. A user's
armory configuration (API endpoint, provider) is personal — the same config can
be used across multiple guilds. **Do NOT add `guild_id`.**

However, the `Guild` model has an `armory_config_id` FK, so the guild→armory
link is already established. No changes needed.

---

### 10.5 Service Layer — Complete Query Audit

Every service file that performs database queries must be audited. Below is the
complete list of changes needed per file.

#### `app/services/signup_service.py` (Highest impact — ~20 queries)

| # | Function | Line | Query type | `guild_id` filter? | Action |
|---|----------|------|-----------|-------------------|--------|
| 1 | `_check_character_ownership()` | 22 | `db.session.get(Character, cid)` | ❌ | Add `char.guild_id == guild_id` check |
| 2 | `_count_assigned_slots()` | 32-37 | `sa.func.count(LineupSlot.id)` | ❌ | Add `.where(LineupSlot.guild_id == guild_id)` |
| 3 | `_count_assigned_slots_locked()` | 50-56 | Count with `with_for_update()` | ❌ | Add `.where(LineupSlot.guild_id == guild_id)` |
| 4 | `_count_user_role_slots()` | 76-86 | JOIN Signup + LineupSlot | ❌ | Add `Signup.guild_id == guild_id` |
| 5 | `_auto_assign_signup()` | 127-181 | Multiple bench/slot queries | ❌ | Add `guild_id` to all sub-queries |
| 6 | `create_signup()` | 259 | `db.session.add(signup)` | ❌ | Set `signup.guild_id = guild_id` |
| 7 | `get_signup()` | 272 | `db.session.get(Signup, id)` | ❌ | Add `guild_id` ownership check |
| 8 | `update_signup()` | 291 | Update by object | ✅ (via caller) | Verify in caller |
| 9 | `delete_signup()` | 315 | Delete by object | ✅ (via caller) | Verify in caller |
| 10 | `list_signups()` | 344-349 | `Signup.raid_event_id == eid` | ❌ | Add `.where(Signup.guild_id == guild_id)` |
| 11 | `list_user_signups()` | 354-362 | Filter by user + events | ❌ | Add `.where(Signup.guild_id == guild_id)` |
| 12 | `get_ban()` | 371-376 | `RaidBan` query | ❌ | Add `.where(RaidBan.guild_id == guild_id)` |
| 13 | `list_bans()` | 382-387 | `RaidBan` query | ❌ | Add `.where(RaidBan.guild_id == guild_id)` |
| 14 | `create_ban()` | 403 | `db.session.add(ban)` | ❌ | Set `ban.guild_id = guild_id` |
| 15 | `delete_ban()` | 413 | Delete by object | ❌ | Add `guild_id` check |
| 16 | `request_replacement()` | 436-455 | Query + insert | ❌ | Add `guild_id` filter; set on new object |
| 17 | `get_pending_replacement()` | 461-472 | CharacterReplacement query | ❌ | Add `guild_id` filter |
| 18 | `list_pending_replacements()` | 478-493 | JOIN query | ❌ | Add `guild_id` filter |
| 19 | `confirm_replacement()` | 522-570 | Complex multi-query | ❌ | Add `guild_id` to all sub-queries |
| 20 | `list_user_characters_for_event()` | 582-588 | Character query | ✅ | Already filters by `guild_id` |

**Function signature changes needed:**
```python
# Most functions need guild_id parameter added:
def create_signup(guild_id, raid_event_id, user_id, character_id, ...) -> Signup:
def list_signups(guild_id, event_id) -> list[Signup]:
def list_user_signups(guild_id, user_id, event_ids) -> list[Signup]:
def create_ban(guild_id, raid_event_id, character_id, banned_by, ...) -> RaidBan:
def get_ban(guild_id, raid_event_id, character_id) -> RaidBan | None:
def list_bans(guild_id, raid_event_id) -> list[RaidBan]:
def request_replacement(guild_id, signup_id, ...) -> CharacterReplacement:
def confirm_replacement(guild_id, replacement_id, ...) -> ...:
```

#### `app/services/lineup_service.py` (~25 queries)

| # | Function | Line | Action |
|---|----------|------|--------|
| 1 | `get_lineup()` | 18-26 | Add `guild_id` param + filter |
| 2 | `has_role_slot()` | — | Internal; called from Signup.to_dict(). Needs guild_id context. |
| 3 | `get_bench_info()` | — | Internal; needs guild_id context. |
| 4 | `add_slot()` | 60-81 | Add `guild_id` param; set on new slot; add to max query |
| 5 | `remove_slot()` | 86-89 | Add `guild_id` filter to delete |
| 6 | `count_role_slots()` | 94-99 | Add `guild_id` filter |
| 7 | `get_bench_slot()` | 109-114 | Add `guild_id` filter |
| 8 | `get_bench_position()` | 124-133 | Add `guild_id` filter |
| 9 | `update_slot_group()` | 145-153 | Add `guild_id` filter |
| 10 | `upsert_slot()` | 164-184 | Add `guild_id` filter + set on new slot |
| 11 | `save_full_lineup()` | 225-397 | Add `guild_id` to delete-all query (line 237); set on every new slot |
| 12 | `reorder_bench()` | 463-512 | Add `guild_id` filter to all queries |
| 13 | `confirm_lineup()` | 541-546 | `guild_id` passed via `get_lineup()` |
| 14 | `add_to_bench_queue()` | 560-561 | Set `guild_id` on new slot |

**Special concern — `has_role_slot()` and `get_bench_info()`:**
These are called from `Signup.to_dict()` which doesn't currently receive
`guild_id`. Options:
1. **Recommended:** These functions query by `signup_id` which is globally unique, so tenant
   filtering is implicitly enforced (a signup belongs to exactly one guild).
   Keep as-is but add a code comment documenting this decision.
2. **Alternative:** Pass `guild_id` through the serialization chain — higher impact, lower risk.

#### `app/services/event_service.py` (~30 queries)

Most queries already filter by `guild_id`. Changes needed:

| # | Function | Line | Action |
|---|----------|------|--------|
| 1 | `get_template()` | 39 | `db.session.get()` — add `guild_id` ownership check |
| 2 | `get_event()` | 287 | `db.session.get()` — add `guild_id` ownership check |
| 3 | `get_series()` | 130 | `db.session.get()` — add `guild_id` ownership check |
| 4 | `duplicate_event()` | 410-426 | Set `guild_id` on new event (already done via `RaidEvent(guild_id=…)`) |
| 5 | All `list_*()` functions | various | Already filter by `guild_id` ✅ |

#### `app/services/attendance_service.py` (~5 queries)

| # | Function | Line | Action |
|---|----------|------|--------|
| 1 | `record_attendance()` | 23-46 | Add `guild_id` param; set on record; add to query |
| 2 | `get_event_attendance()` | 53-57 | Add `guild_id` param + filter |
| 3 | `get_character_history()` | 68-80 | Add `guild_id` param + filter (or intentionally cross-guild for global admins) |

#### `app/services/character_service.py` (~10 queries)

| # | Function | Line | Action |
|---|----------|------|--------|
| 1 | `get_character()` | 59 | Add `guild_id` ownership check after `db.session.get()` |
| 2 | `delete_character()` | 80-125 | Already receives character object; caller ensures guild match |
| 3 | `list_characters()` | 147-152 | Already filters by `guild_id` ✅ |
| 4 | `find_existing_character()` | 157-163 | Already filters by `guild_id` ✅ |

#### `app/services/guild_service.py` (~12 queries)

All queries already properly filter by `guild_id`. No changes needed. ✅

#### `app/services/raid_service.py` (~8 queries)

Most queries already filter by `guild_id`. Verify:
| # | Function | Line | Action |
|---|----------|------|--------|
| 1 | `get_raid_definition()` | 48 | `db.session.get()` — add `guild_id` ownership check |
| 2 | `list_raid_definitions()` | 91-94 | Already filters by `guild_id` ✅ |
| 3 | `find_by_name()` | 81-86 | Already filters by `guild_id` ✅ |

#### `app/services/notification_service.py` (~8 queries)

Notifications are **user-scoped** with optional `guild_id` context. Current
queries filter by `user_id` which is correct — a user sees their own
notifications regardless of guild. No changes needed. ✅

#### `app/services/auth_service.py` (~8 queries)

Global/user-scoped queries. No `guild_id` needed. ✅

#### `app/services/feature_service.py` (~3 queries)

Already filters by `guild_id`. No changes needed. ✅

#### `app/services/discord_service.py` (~4 queries)

Global/user-scoped queries. No `guild_id` needed. ✅

---

### 10.6 API Layer — Complete Route Audit

Every API blueprint must pass `guild_id` from the URL route into the service
layer. Below is the audit for routes that need changes.

#### `app/api/v1/signups.py`

| Route | Method | Current `guild_id` handling | Change |
|-------|--------|---------------------------|--------|
| `/guilds/<guild_id>/events/<eid>/signups` | GET | `guild_id` in URL but not passed to `list_signups()` | Pass `guild_id` to service |
| `/guilds/<guild_id>/events/<eid>/signups` | POST | `guild_id` in URL but not passed to `create_signup()` | Pass `guild_id` to service |
| `/guilds/<guild_id>/events/<eid>/signups/<sid>` | PUT | `guild_id` in URL; event ownership checked | Pass `guild_id` to service |
| `/guilds/<guild_id>/events/<eid>/signups/<sid>` | DELETE | `guild_id` in URL; event ownership checked | Pass `guild_id` to service |
| `/guilds/<guild_id>/events/<eid>/bans` | GET/POST | `guild_id` available | Pass `guild_id` to service |
| `/guilds/<guild_id>/events/<eid>/bans/<bid>` | DELETE | `guild_id` available | Pass `guild_id` to service |
| `/guilds/<guild_id>/events/<eid>/replacements` | GET/POST | `guild_id` available | Pass `guild_id` to service |
| `/guilds/<guild_id>/events/<eid>/replacements/<rid>` | PUT | `guild_id` available | Pass `guild_id` to service |

#### `app/api/v1/lineup.py`

| Route | Method | Change |
|-------|--------|--------|
| `/guilds/<guild_id>/events/<eid>/lineup` | GET | Pass `guild_id` to `get_lineup()` |
| `/guilds/<guild_id>/events/<eid>/lineup` | PUT | Pass `guild_id` to `save_full_lineup()` |
| `/guilds/<guild_id>/events/<eid>/lineup/confirm` | POST | Pass `guild_id` to `confirm_lineup()` |
| `/guilds/<guild_id>/events/<eid>/lineup/bench/reorder` | PUT | Pass `guild_id` to `reorder_bench()` |

#### `app/api/v1/attendance.py`

| Route | Method | Change |
|-------|--------|--------|
| `/guilds/<guild_id>/events/<eid>/attendance` | GET | Pass `guild_id` to `get_event_attendance()` |
| `/guilds/<guild_id>/events/<eid>/attendance` | POST | Pass `guild_id` to `record_attendance()` |

#### `app/api/v1/events.py`

Most event routes already pass `guild_id` correctly. Verify `get_event_or_404()`
checks `event.guild_id == guild_id` (it does — line 43 of `api_helpers.py`). ✅

#### `app/api/v1/admin.py`

Admin dashboard stats queries (`SELECT COUNT(*)`) are **global** — they should
NOT be filtered by `guild_id`. These count all users, all guilds, all events
system-wide. No changes needed. ✅

#### `app/api/v1/roles.py`

Permission and role management is **system-wide**. No `guild_id` filtering
needed. ✅

---

### 10.7 Utility Layer — Query Audit

#### `app/utils/permissions.py`

| Function | Line | Status |
|----------|------|--------|
| `get_membership()` | 23-31 | Already filters by `guild_id` ✅ |
| `has_permission()` | 45-55 | Uses membership from `get_membership()` ✅ |
| `has_any_guild_permission()` | 70-75 | Queries all user memberships (intentionally cross-guild) ✅ |
| `get_user_permissions()` | 109-115 | Uses membership role ✅ |
| `can_grant_role()` | 130-146 | System-wide role check ✅ |

#### `app/utils/api_helpers.py`

| Function | Line | Status |
|----------|------|--------|
| `get_event_or_404()` | 43 | Checks `event.guild_id == guild_id` ✅ |
| `build_guild_role_map()` | 62-67 | Already filters by `guild_id` ✅ |

#### `app/utils/notify.py`

| Function | Line | Status |
|----------|------|--------|
| `_get_officer_user_ids()` | 47-61 | Filters by `guild_id` ✅ |
| `_guild_member_ids()` | 85-94 | Filters by `guild_id` ✅ |
| All `notify_*()` | various | Use `event.guild_id` ✅ |

#### `app/utils/decorators.py`

| Function | Line | Status |
|----------|------|--------|
| `guild_permission_required()` | 5-16 | Extracts `guild_id` from URL kwargs ✅ |

---

### 10.8 Background Jobs — Query Audit

#### `app/jobs/handlers.py`

| Function | Line | Status | Change |
|----------|------|--------|--------|
| `handle_send_notification()` | 31-38 | `guild_id` from payload | No change — notification uses `guild_id` from payload ✅ |
| `auto_lock_upcoming_events()` | 56-79 | Queries all events (intentionally cross-guild for scheduler) | No change — global scheduler job ✅ |
| `handle_sync_characters()` | 93-144 | Optional `guild_id` filter for character sync | Already filters by `guild_id` when provided ✅ |

#### `app/jobs/worker.py`

| Function | Line | Status |
|----------|------|--------|
| `claim_next_job()` | 17-25 | Global job queue (not tenant-scoped) ✅ |

#### `app/jobs/scheduler.py`

| Function | Line | Status |
|----------|------|--------|
| All | — | Global system settings (not tenant-scoped) ✅ |

---

### 10.9 Seed Data — Impact Assessment

#### `app/seeds/permissions.py`

No changes needed. Permissions and system roles are **global** — they apply to
all guilds equally. `guild_id` is not involved. ✅

#### `app/seeds/raid_definitions.py`

No changes needed. Default raid definitions use `guild_id=None` (builtin).
Guild-specific definitions already have `guild_id` set. ✅

#### `app/seeds/admin_user.py`

No changes needed. Admin user is a global user, not tied to a specific guild. ✅

---

### 10.10 Implementation Strategy — Recommended Approach

#### Option A: `TenantMixin` Base Class (Recommended)

Create a mixin that automatically adds `guild_id` and provides tenant-scoped
query helpers:

```python
# app/models/mixins.py (NEW FILE)

class TenantMixin:
    """Mixin for models that are scoped to a guild (tenant).

    Adds guild_id FK and provides helper methods for tenant-scoped queries.
    """

    @declared_attr
    def guild_id(cls):
        return mapped_column(
            sa.Integer,
            sa.ForeignKey("guilds.id"),
            nullable=False,
            index=True,
        )

    @declared_attr
    def guild(cls):
        return relationship("Guild", foreign_keys=[cls.guild_id], lazy="select")

    @classmethod
    def tenant_query(cls, guild_id: int):
        """Return a base query filtered by guild_id."""
        return sa.select(cls).where(cls.guild_id == guild_id)

    @classmethod
    def tenant_filter(cls, guild_id: int):
        """Return a WHERE clause for guild_id filtering."""
        return cls.guild_id == guild_id
```

**Usage in models:**
```python
class Signup(TenantMixin, db.Model):
    # guild_id and guild relationship are inherited from TenantMixin
    ...
```

**Usage in services:**
```python
# Before:
stmt = sa.select(Signup).where(Signup.raid_event_id == event_id)

# After:
stmt = sa.select(Signup).where(
    Signup.guild_id == guild_id,
    Signup.raid_event_id == event_id,
)

# Or using helper:
stmt = Signup.tenant_query(guild_id).where(Signup.raid_event_id == event_id)
```

#### Option B: `@filter_by_tenant` Query Decorator

Create a decorator that automatically injects `guild_id` filtering:

```python
# app/utils/tenant.py (NEW FILE)

def tenant_scoped(model_class):
    """Decorator for service functions that need tenant scoping.

    Automatically adds guild_id filter to the first sa.select() call.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(guild_id, *args, **kwargs):
            # Inject guild_id into the function's scope
            return func(guild_id, *args, **kwargs)
        return wrapper
    return decorator
```

**Verdict:** Option A (`TenantMixin`) is simpler, more explicit, and easier to
audit. **Use Option A.**

---

### 10.11 Database Migration — Step-by-Step

The migration must be executed as a **single Alembic migration** to maintain
atomicity. Here is the exact sequence:

```python
# migrations/versions/xxxx_add_guild_id_to_child_tables.py

def upgrade():
    # Step 1: Add guild_id columns (nullable initially for backfill)
    op.add_column('signups', sa.Column('guild_id', sa.Integer(), nullable=True))
    op.add_column('lineup_slots', sa.Column('guild_id', sa.Integer(), nullable=True))
    op.add_column('raid_bans', sa.Column('guild_id', sa.Integer(), nullable=True))
    op.add_column('attendance_records', sa.Column('guild_id', sa.Integer(), nullable=True))
    op.add_column('character_replacements', sa.Column('guild_id', sa.Integer(), nullable=True))

    # Step 2: Backfill guild_id from parent relationships
    # signups → raid_events.guild_id
    op.execute("""
        UPDATE signups SET guild_id = (
            SELECT raid_events.guild_id FROM raid_events
            WHERE raid_events.id = signups.raid_event_id
        )
    """)

    # lineup_slots → raid_events.guild_id
    op.execute("""
        UPDATE lineup_slots SET guild_id = (
            SELECT raid_events.guild_id FROM raid_events
            WHERE raid_events.id = lineup_slots.raid_event_id
        )
    """)

    # raid_bans → raid_events.guild_id
    op.execute("""
        UPDATE raid_bans SET guild_id = (
            SELECT raid_events.guild_id FROM raid_events
            WHERE raid_events.id = raid_bans.raid_event_id
        )
    """)

    # attendance_records → raid_events.guild_id
    op.execute("""
        UPDATE attendance_records SET guild_id = (
            SELECT raid_events.guild_id FROM raid_events
            WHERE raid_events.id = attendance_records.raid_event_id
        )
    """)

    # character_replacements → signups → raid_events.guild_id (2-hop)
    op.execute("""
        UPDATE character_replacements SET guild_id = (
            SELECT raid_events.guild_id FROM signups
            JOIN raid_events ON raid_events.id = signups.raid_event_id
            WHERE signups.id = character_replacements.signup_id
        )
    """)

    # Step 3: Make columns NOT NULL
    op.alter_column('signups', 'guild_id', nullable=False)
    op.alter_column('lineup_slots', 'guild_id', nullable=False)
    op.alter_column('raid_bans', 'guild_id', nullable=False)
    op.alter_column('attendance_records', 'guild_id', nullable=False)
    op.alter_column('character_replacements', 'guild_id', nullable=False)

    # Step 4: Add foreign key constraints
    op.create_foreign_key('fk_signups_guild', 'signups', 'guilds', ['guild_id'], ['id'])
    op.create_foreign_key('fk_lineup_slots_guild', 'lineup_slots', 'guilds', ['guild_id'], ['id'])
    op.create_foreign_key('fk_raid_bans_guild', 'raid_bans', 'guilds', ['guild_id'], ['id'])
    op.create_foreign_key('fk_attendance_records_guild', 'attendance_records', 'guilds', ['guild_id'], ['id'])
    op.create_foreign_key('fk_character_replacements_guild', 'character_replacements', 'guilds', ['guild_id'], ['id'])

    # Step 5: Add indexes for tenant-scoped queries
    op.create_index('ix_signups_guild', 'signups', ['guild_id'])
    op.create_index('ix_signups_guild_event', 'signups', ['guild_id', 'raid_event_id'])
    op.create_index('ix_lineup_slots_guild', 'lineup_slots', ['guild_id'])
    op.create_index('ix_lineup_slots_guild_event', 'lineup_slots', ['guild_id', 'raid_event_id'])
    op.create_index('ix_raid_bans_guild', 'raid_bans', ['guild_id'])
    op.create_index('ix_attendance_records_guild', 'attendance_records', ['guild_id'])
    op.create_index('ix_character_replacements_guild', 'character_replacements', ['guild_id'])


def downgrade():
    # Remove indexes
    op.drop_index('ix_character_replacements_guild', 'character_replacements')
    op.drop_index('ix_attendance_records_guild', 'attendance_records')
    op.drop_index('ix_raid_bans_guild', 'raid_bans')
    op.drop_index('ix_lineup_slots_guild_event', 'lineup_slots')
    op.drop_index('ix_lineup_slots_guild', 'lineup_slots')
    op.drop_index('ix_signups_guild_event', 'signups')
    op.drop_index('ix_signups_guild', 'signups')

    # Remove foreign keys
    op.drop_constraint('fk_character_replacements_guild', 'character_replacements', type_='foreignkey')
    op.drop_constraint('fk_attendance_records_guild', 'attendance_records', type_='foreignkey')
    op.drop_constraint('fk_raid_bans_guild', 'raid_bans', type_='foreignkey')
    op.drop_constraint('fk_lineup_slots_guild', 'lineup_slots', type_='foreignkey')
    op.drop_constraint('fk_signups_guild', 'signups', type_='foreignkey')

    # Remove columns
    op.drop_column('character_replacements', 'guild_id')
    op.drop_column('attendance_records', 'guild_id')
    op.drop_column('raid_bans', 'guild_id')
    op.drop_column('lineup_slots', 'guild_id')
    op.drop_column('signups', 'guild_id')
```

---

### 10.12 Verification & Testing Plan

#### Pre-migration verification:
```sql
-- Count rows in each table BEFORE migration
SELECT 'signups' AS tbl, COUNT(*) AS cnt FROM signups
UNION ALL SELECT 'lineup_slots', COUNT(*) FROM lineup_slots
UNION ALL SELECT 'raid_bans', COUNT(*) FROM raid_bans
UNION ALL SELECT 'attendance_records', COUNT(*) FROM attendance_records
UNION ALL SELECT 'character_replacements', COUNT(*) FROM character_replacements;
```

#### Post-migration verification:
```sql
-- Verify NO nulls remain after backfill
SELECT 'signups' AS tbl, COUNT(*) AS nulls FROM signups WHERE guild_id IS NULL
UNION ALL SELECT 'lineup_slots', COUNT(*) FROM lineup_slots WHERE guild_id IS NULL
UNION ALL SELECT 'raid_bans', COUNT(*) FROM raid_bans WHERE guild_id IS NULL
UNION ALL SELECT 'attendance_records', COUNT(*) FROM attendance_records WHERE guild_id IS NULL
UNION ALL SELECT 'character_replacements', COUNT(*) FROM character_replacements WHERE guild_id IS NULL;

-- Verify guild_id matches parent chain
SELECT COUNT(*) AS mismatches
FROM signups s
JOIN raid_events re ON re.id = s.raid_event_id
WHERE s.guild_id != re.guild_id;
-- Expected: 0

SELECT COUNT(*) AS mismatches
FROM lineup_slots ls
JOIN raid_events re ON re.id = ls.raid_event_id
WHERE ls.guild_id != re.guild_id;
-- Expected: 0

SELECT COUNT(*) AS mismatches
FROM raid_bans rb
JOIN raid_events re ON re.id = rb.raid_event_id
WHERE rb.guild_id != re.guild_id;
-- Expected: 0

SELECT COUNT(*) AS mismatches
FROM attendance_records ar
JOIN raid_events re ON re.id = ar.raid_event_id
WHERE ar.guild_id != re.guild_id;
-- Expected: 0

SELECT COUNT(*) AS mismatches
FROM character_replacements cr
JOIN signups s ON s.id = cr.signup_id
JOIN raid_events re ON re.id = s.raid_event_id
WHERE cr.guild_id != re.guild_id;
-- Expected: 0
```

#### New integration tests to add:

```python
# tests/test_tenant_isolation.py (NEW FILE)

class TestTenantIsolation:
    """Verify that guild-scoped data is properly isolated between tenants."""

    def test_signup_cannot_see_other_guild_signups(self):
        """Signups from Guild A must NOT appear in Guild B queries."""

    def test_lineup_cannot_see_other_guild_slots(self):
        """Lineup slots from Guild A must NOT appear in Guild B queries."""

    def test_attendance_cannot_see_other_guild_records(self):
        """Attendance records from Guild A must NOT appear in Guild B queries."""

    def test_ban_cannot_see_other_guild_bans(self):
        """Raid bans from Guild A must NOT appear in Guild B queries."""

    def test_replacement_cannot_see_other_guild_replacements(self):
        """Character replacements from Guild A must NOT appear in Guild B."""

    def test_event_cannot_access_other_guild_event(self):
        """An event_id from Guild A should not be accessible from Guild B context."""

    def test_character_cannot_signup_to_other_guild_event(self):
        """A character from Guild A cannot sign up for a Guild B event."""

    def test_admin_dashboard_sees_all_guilds(self):
        """Global admin dashboard should count ALL guilds (not tenant-filtered)."""

    def test_notification_visible_across_guilds(self):
        """User notifications are user-scoped, not guild-scoped."""

    def test_global_roles_not_tenant_scoped(self):
        """System roles and permissions are global, not per-guild."""
```

#### Existing test regression:
```bash
# Run full suite after every model change:
python -m pytest tests/ -v
# Expected: all 632+ tests pass (some may need guild_id added to fixtures)
```

---

### 10.13 Test Fixture Changes

Many existing tests create signups, lineup slots, bans, and attendance records
without setting `guild_id` (since the column doesn't exist yet). After adding
the column, these tests will fail because `guild_id` is `NOT NULL`.

**Approach:** Update test fixtures/factories to include `guild_id`:

```python
# Before (current test fixtures):
signup = Signup(
    raid_event_id=event.id,
    user_id=user.id,
    character_id=char.id,
    chosen_role="melee_dps",
)

# After (with guild_id):
signup = Signup(
    guild_id=guild.id,          # NEW — required
    raid_event_id=event.id,
    user_id=user.id,
    character_id=char.id,
    chosen_role="melee_dps",
)
```

**Files that will need fixture updates (estimate):**

| Test file | Affected fixtures | Estimated changes |
|-----------|-------------------|-------------------|
| `tests/test_signups.py` | Signup creation | ~15-25 places |
| `tests/test_lineup.py` | LineupSlot creation | ~20-30 places |
| `tests/test_attendance.py` | AttendanceRecord creation | ~5-10 places |
| `tests/test_events.py` | Event + signup chains | ~10-15 places |
| `tests/test_replacements.py` | CharacterReplacement creation | ~5-10 places |
| `tests/test_permissions.py` | Various through full-stack tests | ~5-10 places |
| Other test files | Various | ~10-20 places |

**Total estimated:** 70-120 test fixture updates across ~20 test files.

---

### 10.14 Rollout Checklist

Execute these steps **in order**. Each step must be verified before proceeding.

- [ ] **Step 0.1:** Create `app/models/mixins.py` with `TenantMixin`
- [ ] **Step 0.2:** Add `TenantMixin` to `Signup` model — run tests (expect failures)
- [ ] **Step 0.3:** Update test fixtures for `Signup.guild_id` — run tests (expect pass)
- [ ] **Step 0.4:** Update `signup_service.py` — add `guild_id` params + filters to all queries
- [ ] **Step 0.5:** Update `app/api/v1/signups.py` — pass `guild_id` to service calls
- [ ] **Step 0.6:** Run full test suite — all signup tests pass ✅
- [ ] **Step 0.7:** Add `TenantMixin` to `LineupSlot` model — run tests (expect failures)
- [ ] **Step 0.8:** Update test fixtures for `LineupSlot.guild_id` — run tests
- [ ] **Step 0.9:** Update `lineup_service.py` — add `guild_id` params + filters
- [ ] **Step 0.10:** Update `app/api/v1/lineup.py` — pass `guild_id` to service calls
- [ ] **Step 0.11:** Run full test suite — all lineup tests pass ✅
- [ ] **Step 0.12:** Add `TenantMixin` to `RaidBan` model — run tests (expect failures)
- [ ] **Step 0.13:** Update test fixtures for `RaidBan.guild_id` — run tests
- [ ] **Step 0.14:** Update `signup_service.py` ban functions — add `guild_id` filters
- [ ] **Step 0.15:** Run full test suite — all ban tests pass ✅
- [ ] **Step 0.16:** Add `TenantMixin` to `AttendanceRecord` model — run tests (expect failures)
- [ ] **Step 0.17:** Update test fixtures for `AttendanceRecord.guild_id` — run tests
- [ ] **Step 0.18:** Update `attendance_service.py` — add `guild_id` params + filters
- [ ] **Step 0.19:** Update `app/api/v1/attendance.py` — pass `guild_id` to service calls
- [ ] **Step 0.20:** Run full test suite — all attendance tests pass ✅
- [ ] **Step 0.21:** Add `TenantMixin` to `CharacterReplacement` model — run tests (expect failures)
- [ ] **Step 0.22:** Update test fixtures for `CharacterReplacement.guild_id` — run tests
- [ ] **Step 0.23:** Update `signup_service.py` replacement functions — add `guild_id` filters
- [ ] **Step 0.24:** Run full test suite — all replacement tests pass ✅
- [ ] **Step 0.25:** Write and run the Alembic migration script
- [ ] **Step 0.26:** Run post-migration verification queries
- [ ] **Step 0.27:** Write `tests/test_tenant_isolation.py` — cross-tenant isolation tests
- [ ] **Step 0.28:** Run full test suite — all 632+ tests pass ✅
- [ ] **Step 0.29:** Manual smoke test — create 2 guilds, create events/signups in each, verify isolation
- [ ] **Step 0.30:** Code review — audit every query in the codebase for missing `guild_id` filters

---

### 10.15 Summary of All Changes

| Area | Files | Estimated changes |
|------|-------|-------------------|
| **New files** | `app/models/mixins.py` | 1 new file (~30 lines) |
| **Model changes** | `app/models/signup.py` (Signup, LineupSlot, RaidBan, CharacterReplacement), `app/models/attendance.py` (AttendanceRecord) — 5 models across 2 files | ~25 lines total |
| **Service changes** | `signup_service.py`, `lineup_service.py`, `attendance_service.py`, `event_service.py`, `character_service.py`, `raid_service.py` | ~60-80 query updates |
| **API changes** | `signups.py`, `lineup.py`, `attendance.py` | ~15-20 parameter additions |
| **Test fixtures** | 10-20 test files | ~70-120 fixture updates |
| **New tests** | `tests/test_tenant_isolation.py` | 1 new file (~10 tests) |
| **Migration** | Alembic migration file | 1 file (~100 lines) |
| **Total** | ~25-35 files | ~200-300 lines changed |

### 10.16 What This Does NOT Cover

The following are explicitly **out of scope** for Phase 0 and will be addressed
in later phases:

| Item | Phase | Reason |
|------|-------|--------|
| Invitation-based guild membership | Phase 2 | Separate feature, not a tenancy concern |
| Per-guild role customization | Phase 3 | Requires expansion system first |
| Multi-expansion support | Phase 4 | Build on top of tenant-isolated foundation |
| Plugin architecture | Phase 5 | Build on top of tenant-isolated foundation |
| Billing/subscription per guild | Phase 6 | Requires tenant isolation (done in Phase 0) |
| Row-level security (Postgres RLS) | Future | Advanced DB-level enforcement; Phase 0 uses application-level enforcement |
| Separate databases per tenant | Never | Over-engineering for this application's scale |

### 10.17 Decision Record

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Use application-level tenant filtering (not Postgres RLS) | App uses SQLite in dev; RLS is Postgres-only. Application-level is portable. |
| 2 | Add `guild_id` as denormalized column (not just rely on FK chain) | 1-hop lookup is faster and safer than 2-3 hop JOINs. Denormalization is acceptable for read-heavy workload. |
| 3 | Use `TenantMixin` (not decorator) | Explicit is better than implicit. Mixin makes guild_id visible in model definition. |
| 4 | Migrate all 5 tables in one Alembic migration | Atomic migration prevents half-migrated state. Easier to rollback. |
| 5 | Do Phase 0 before all other phases | Retrofitting tenancy after Phases 1-5 would require re-auditing every new query. Pay the cost once, upfront. |
| 6 | Keep `armory_configs` without `guild_id` | User-scoped, not guild-scoped. Guild links via `Guild.armory_config_id` FK. |
| 7 | Keep `notifications` `guild_id` nullable | Some notifications are system-wide (password change, etc.). User-scoped queries are correct. |
| 8 | Keep unique constraints event-scoped (not guild-scoped) | Events already belong to exactly one guild. Adding guild_id to unique constraints is redundant. |
