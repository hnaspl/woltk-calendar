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
3. [Per-User Tenancy & Multi-Tenancy Redesign](#3-per-user-tenancy--multi-tenancy-redesign)
4. [Expansion-Aware Class/Role/Spec System](#4-expansion-aware-classrolespec-system)
5. [Class → Role Ability Matrix for Guild Admins](#5-class--role-ability-matrix-for-guild-admins)
6. [Plugin Architecture](#6-plugin-architecture)
7. [Phased Implementation Roadmap](#7-phased-implementation-roadmap)
8. [Migration & Backward Compatibility](#8-migration--backward-compatibility)
9. [Open Questions & Decisions](#9-open-questions--decisions)
10. [Phase 0: Per-User Tenancy — Detailed Plan](#10-phase-0-per-user-tenancy--detailed-plan)
11. [Frontend Multi-Tenant Migration — Complete Plan](#11-frontend-multi-tenant-migration--complete-plan)
12. [Frontend Testing Strategy for Multi-Tenancy](#12-frontend-testing-strategy-for-multi-tenancy)
13. [Cleanup Protocol — Per-Phase Code Hygiene](#13-cleanup-protocol--per-phase-code-hygiene)

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

## 3. Per-User Tenancy & Multi-Tenancy Redesign

### 3.1 Problem Statement

Currently, any registered user can:
- See all guilds in the system
- Self-join any guild (if `allow_self_join=True`, which is the default)
- Be a member of multiple guilds simultaneously
- There is no concept of isolated user workspaces — all guilds exist in a shared global namespace

This is **not SaaS-safe** because:
- No data isolation between users' workspaces
- No control over who accesses guild data
- No billing boundary per user/organization
- No per-user limits on resource creation (guilds, events, etc.)
- Users cannot have their "own application" experience

### 3.2 Proposed Solution: Per-User Tenant Model

**Clarification:** By "multi-tenant," we mean **per-user tenants** — a true SaaS
model where each registered user gets their own **tenant** (workspace). Within
that workspace, the tenant owner can create guilds (up to a configurable limit),
manage events, invite players, and operate as if they have their own dedicated
application instance. The only shared infrastructure is the underlying database
and the global admin panel.

> **Key insight:** Each tenant behaves like a standalone application instance for
> its owner. Data between tenants is completely isolated. Users invited to
> multiple tenants can switch between them in real time from the sidebar.

**Why per-user tenants (not per-guild)?**
- Guild is an organizational unit **within** a tenant, not the tenant boundary itself
- A single user may want to run multiple guilds (e.g., a main raiding guild + a casual alt guild)
- Billing and resource limits should be per person/organization, not per guild
- Users invited into someone else's workspace should see that workspace's data only while active in it
- This matches true SaaS patterns (Slack, Discord, Notion, etc.) where each workspace is separate

#### 3.2.1 Tenant Lifecycle

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           TENANT LIFECYCLE                                     │
│                                                                                │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │ User          │    │ Tenant auto-     │    │ Owner creates guilds         │  │
│  │ registers     │───▶│ created for user │───▶│ (up to plan limit)           │  │
│  │ on platform   │    │ (user = owner)   │    │ within their tenant          │  │
│  └──────────────┘    └──────────────────┘    └───────────────┬──────────────┘  │
│                                                               │                │
│                        ┌─────────────────────────────────────┘                │
│                        │                                                       │
│           ┌────────────▼──────────────┐                                        │
│           │ Owner invites players     │                                        │
│           │ to their tenant via:      │                                        │
│           │  • Shareable invite link  │                                        │
│           │  • Discord OAuth invite   │                                        │
│           │  • Direct in-app invite   │                                        │
│           └────────────┬──────────────┘                                        │
│                        │                                                       │
│           ┌────────────▼──────────────┐    ┌───────────────────────────────┐   │
│           │ Invited user accepts      │    │ User sees multiple tenants    │   │
│           │ → becomes tenant member   │───▶│ in sidebar, switches in       │   │
│           │ with assigned role        │    │ real time                     │   │
│           └───────────────────────────┘    └───────────────────────────────┘   │
│                                                                                │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │ GLOBAL ADMIN (platform-wide):                                             │ │
│  │  • View/manage all tenants          • Suspend/delete tenants              │ │
│  │  • Override tenant limits           • View platform-wide statistics       │ │
│  │  • Manage global settings           • Manage system roles/permissions     │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 Tenant Model

New `Tenant` model — the top-level isolation boundary:

```python
class Tenant(db.Model):
    """Per-user workspace. Each user who registers gets one tenant.
    Think of it as 'your own application instance' — separate data,
    separate guilds, separate members."""

    __tablename__ = "tenants"

    id            = Column(Integer, primary_key=True)
    name          = Column(String(100), nullable=False)        # Display name (e.g., "Arthas's Workspace")
    slug          = Column(String(100), unique=True, nullable=False)  # URL-friendly identifier
    owner_id      = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
                    # unique=True → each user owns exactly one tenant. Drop unique if
                    # multi-workspace support is needed in the future.
    plan          = Column(String(30), default="free")         # free / pro / enterprise (future billing)
    max_guilds    = Column(Integer, default=3)                 # Guild limit per plan
    max_members   = Column(Integer, default=50)                # Member limit per plan
    is_active     = Column(Boolean, default=True)              # Global admin can suspend
    settings_json = Column(Text, nullable=True)                # Tenant-level overrides
    created_at    = Column(DateTime, default=utcnow)
    updated_at    = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    owner         = relationship("User", foreign_keys=[owner_id], backref="owned_tenant")
    memberships   = relationship("TenantMembership", back_populates="tenant", cascade="all, delete-orphan")
    guilds        = relationship("Guild", back_populates="tenant", cascade="all, delete-orphan")
```

#### 3.2.3 Tenant Membership Model

Users can be members of multiple tenants (their own + ones they're invited to):

```python
class TenantMembership(db.Model):
    """Links a user to a tenant. The tenant owner always has an 'owner'
    membership. Other users are invited and get 'member' or 'admin' roles."""

    __tablename__ = "tenant_memberships"

    id          = Column(Integer, primary_key=True)
    tenant_id   = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    role        = Column(String(30), default="member")   # owner / admin / member
    status      = Column(Enum(MemberStatus), default=MemberStatus.ACTIVE)
    created_at  = Column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )

    tenant = relationship("Tenant", back_populates="memberships")
    user   = relationship("User", backref="tenant_memberships")
```

#### 3.2.4 Tenant Invitation Model

```python
class TenantInvitation(db.Model):
    """Invitation to join a tenant workspace."""

    __tablename__ = "tenant_invitations"

    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    inviter_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    invitee_email   = Column(String(255), nullable=True)    # For email-based invites
    invitee_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    invite_token    = Column(String(64), unique=True, nullable=False)  # Shareable link token
    role            = Column(String(30), default="member")  # Role on acceptance
    status          = Column(String(20), default="pending") # pending / accepted / declined / expired
    expires_at      = Column(DateTime, nullable=True)       # NULL = never expires
    created_at      = Column(DateTime, default=utcnow)
    accepted_at     = Column(DateTime, nullable=True)

    tenant  = relationship("Tenant")
    inviter = relationship("User", foreign_keys=[inviter_id])
    invitee = relationship("User", foreign_keys=[invitee_user_id])
```

#### 3.2.5 Invitation Channels

Players can be invited to a tenant via multiple channels:

| Channel | How It Works | Best For |
|---------|-------------|----------|
| **Shareable Link** | Generate a unique invite URL (`/invite/{token}`). Anyone with the link can join. Can be single-use or multi-use with expiry. | Quick sharing in-game, forums, chat |
| **Discord OAuth** | Tenant owner connects Discord. Bot sends DM or channel invite with link. Invited user logs in via Discord OAuth → auto-joins tenant. | WoW guilds that already use Discord |
| **Direct In-App** | Search for existing users by username and send a direct invite notification. Invitee sees it in their notification panel. | Users already on the platform |
| **Email** (future) | Send invite to email address. If user doesn't have an account, they register first, then auto-join the tenant. | Reaching players not yet on platform |

#### 3.2.6 Guild Membership (Within Tenant)

Within a tenant, guild membership works similarly to the current model but is
**always scoped to the tenant**:

```python
class MemberStatus(str, Enum):
    ACTIVE = "active"          # Full member (existing)
    INVITED = "invited"        # Invited, pending acceptance (existing)
    BANNED = "banned"          # Banned from guild (existing)
    APPLIED = "applied"              # NEW: User applied, pending admin approval
    INVITE_DECLINED = "invite_declined"   # NEW: User declined an invitation
    APPLICATION_REJECTED = "application_rejected"  # NEW: Admin rejected
```

Guild visibility within a tenant:

```python
class GuildVisibility(str, Enum):
    PRIVATE = "private"      # Only visible to assigned members within the tenant
    OPEN = "open"            # All tenant members can see and self-join
```

> **Note:** Cross-tenant guild discovery is intentionally not supported. A user
> must first be a member of a tenant before they can see or join guilds within it.

#### 3.2.7 Data Access Boundaries

All data is isolated by `tenant_id`. A user can only see data from the tenant
they are currently viewing:

| Data | Current Access | Proposed Access |
|------|---------------|-----------------|
| Guild list | All guilds visible | Only guilds in active tenant |
| Guild details | Any authenticated user | Tenant members only |
| Events | Visible to all guild members | Scoped to tenant + guild |
| Characters | Visible across guilds | Scoped to tenant + guild |
| Attendance | Guild-scoped | Tenant + guild-scoped |
| Notifications | User-scoped | User-scoped (cross-tenant — user sees notifications from all their tenants) |
| Raid definitions | Global + guild-scoped | Global + tenant + guild-scoped |

#### 3.2.8 New Permissions

```python
# Tenant-level permissions (new category):
("manage_tenant_members", "Manage Tenant Members", "Invite/remove members from tenant", "tenant"),
("manage_tenant_settings", "Manage Tenant Settings", "Change tenant name, limits, settings", "tenant"),

# Guild-level permissions (existing + new):
("invite_members", "Invite Members", "Send guild invitations within tenant", "guild"),
("approve_applications", "Approve Applications", "Approve/decline guild membership applications", "guild"),
("manage_guild_visibility", "Manage Guild Visibility", "Change guild visibility within tenant", "guild"),
```

### 3.3 Tenancy Approach Comparison

| Approach | Pros | Cons | Our Decision |
|----------|------|------|--------------|
| **Full tenant isolation** (DB per tenant) | Complete data separation | Heavy infrastructure, complex ops | ❌ Over-engineering for this scale |
| **Schema-based multi-tenancy** (schema per tenant) | Good isolation | Complex migrations, Postgres-only | ❌ Too complex |
| **Row-level tenancy** (tenant_id on every table) ✅ | Simple, shared DB, cross-tenant possible | Must enforce on every query | ✅ **Selected** |
| **Guild-as-tenant** (guild_id = tenant boundary) | Simple | 1 user = 1 guild limit, no workspace concept | ❌ Doesn't match SaaS model |

**Decision:** Use **row-level tenancy with per-user tenants**. Each user gets a
`Tenant` record. Every guild-scoped table carries a `tenant_id` FK. The
application enforces `WHERE tenant_id = ?` on every query. This gives each user
the experience of having their own application while sharing a single database.

> **Implementation:** The complete table-by-table, query-by-query change plan is
> in [Section 10: Phase 0](#10-phase-0-per-user-tenancy--detailed-plan).

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

### Phase 0: Per-User Tenancy (`tenant_id` on every table)
**Goal:** Introduce a per-user tenant model and remodel the entire application to
enforce row-level tenant isolation (`tenant_id` on every guild-scoped table)
**before** any feature work. Each registered user gets a Tenant (workspace) and
all data is scoped by `tenant_id`.

> **This phase is a prerequisite for all other phases.** See
> [Section 10](#10-phase-0-per-user-tenancy--detailed-plan) for the
> complete table-by-table, query-by-query, file-by-file change plan.

- [ ] Create `Tenant` model (owner = user, plan, limits, settings)
- [ ] Create `TenantMembership` model (user ↔ tenant link with role)
- [ ] Create `TenantInvitation` model (invite link, Discord, in-app)
- [ ] Auto-create a tenant for each user on registration
- [ ] Add `tenant_id` FK to `guilds` table (Guild belongs to Tenant)
- [ ] Add `tenant_id` FK to all guild-child tables (characters, events, signups, lineup_slots, raid_bans, attendance_records, character_replacements, etc.)
- [ ] Data migration: backfill `tenant_id` from owner relationships
- [ ] Add composite indexes on `(tenant_id, ...)` for all tenant-scoped tables
- [ ] Update every service-layer query to include `tenant_id` filter
- [ ] Update every API route to pass `tenant_id` through the call chain
- [ ] Add `TenantMixin` for models with automatic `tenant_id` column
- [ ] Build tenant invitation endpoints (create/accept/decline invite links)
- [ ] Build tenant switching API + frontend sidebar component
- [ ] Add Tenants tab to global admin panel
- [ ] Add tests verifying cross-tenant data isolation
- [ ] Regression-test all 632+ existing tests
- [ ] **🧹 Phase 0 cleanup** (see [§13.3.1](#1331-phase-0-cleanup-checklist)):
  - [ ] Delete orphaned `src/components/admin/SystemTab.vue` (unused, replaced by UsersTab + SettingsTab)
  - [ ] Remove pre-tenant `allow_self_join` guild-level self-join flow from AppSidebar (replaced by tenant invitation system)
  - [ ] Remove "available guilds to join" sidebar section (guild discovery now happens within tenant)
  - [ ] Audit and remove any temporary migration helpers/scripts
  - [ ] Verify no dead imports remain after model/service changes
  - [ ] Run full lint + build + test suite on clean branch

### Phase 1: Foundation Decoupling (No Breaking Changes)
**Goal:** Restructure internals without changing any external behavior.

- [ ] Create `app/expansions/` directory with expansion registry
- [ ] Move `CLASS_ROLES`, `CLASS_SPECS`, `WOTLK_RAIDS` from `constants.py` into expansion-specific config files
- [ ] Keep backward compatibility: `constants.py` imports from `app/expansions/wotlk.py`
- [ ] Add `expansion` field to Guild model (default: `"wotlk"`)
- [ ] Make `meta.py` constants endpoint expansion-aware (with backward-compatible default)
- [ ] Add expansion-aware validation in character service
- [ ] All existing tests must pass unchanged
- [ ] **🧹 Phase 1 cleanup** (see [§13.3.2](#1332-phase-1-cleanup-checklist)):
  - [ ] Remove hardcoded `WOTLK_RAIDS` from `app/constants.py` after moving to `app/expansions/wotlk.py`
  - [ ] Remove hardcoded `CLASS_ROLES` / `CLASS_SPECS` from `app/constants.py` (keep backward-compat re-exports only)
  - [ ] Delete any temporary backward-compat shims that are no longer needed
  - [ ] Verify no file imports the old location directly (all go through expansion registry)
  - [ ] Run full lint + build + test suite on clean branch

### Phase 2: Guild Membership Hardening (Within Tenant)
**Goal:** Give guild admins control over guild membership within their tenant.

- [ ] Add `GuildVisibility` enum and `visibility` field to Guild model
- [ ] Add `GuildInvitation` model (guild-level invites within a tenant)
- [ ] Extend `MemberStatus` with `APPLIED` and `DECLINED`
- [ ] Create guild invitation endpoints (send, accept, decline, list)
- [ ] Create application endpoints (apply, approve, decline)
- [ ] Add `invite_members` and `approve_applications` permissions
- [ ] Update guild list endpoint to respect visibility settings within tenant
- [ ] Change `allow_self_join` default to `False`
- [ ] Build invitation management UI (guild admin panel)
- [ ] Add guild discovery page (open guilds within tenant only)
- [ ] **🧹 Phase 2 cleanup** (see [§13.3.3](#1333-phase-2-cleanup-checklist)):
  - [ ] Remove or deprecate `allow_self_join` field from Guild model if fully replaced by invitation system
  - [ ] Remove any remaining direct-join logic (old `POST /guilds/{id}/join` flow without invitation)
  - [ ] Clean up old guild membership test fixtures that bypass invitation flow
  - [ ] Verify no frontend code references removed join flows
  - [ ] Run full lint + build + test suite on clean branch

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
- [ ] **🧹 Phase 3 cleanup** (see [§13.3.4](#1334-phase-3-cleanup-checklist)):
  - [ ] Remove hardcoded class→role validation from signup/lineup services (replaced by matrix resolution)
  - [ ] Remove static `CLASS_ROLES` usage in signup validation (should use guild-specific matrix)
  - [ ] Clean up any compatibility shims between old static mapping and new matrix system
  - [ ] Run full lint + build + test suite on clean branch

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
- [ ] **🧹 Phase 4 cleanup** (see [§13.3.5](#1335-phase-4-cleanup-checklist)):
  - [ ] Remove WotLK-only assumptions from `src/constants.js` (static `WOW_CLASSES`, `RAID_TYPES`)
  - [ ] Remove Phase 1 backward-compat re-exports in `app/constants.py` if no longer used
  - [ ] Remove hardcoded WotLK class list from `CharacterManagerView.vue` (should come from expansion-aware constants store)
  - [ ] Verify `normalizeSpecName()` handles all expansion specs, remove any WotLK-only branches
  - [ ] Clean up dead expansion-related code paths (e.g., `if expansion === 'wotlk'` branches that are now generic)
  - [ ] Run full lint + build + test suite on clean branch

### Phase 5: Plugin Architecture
**Goal:** Make features truly pluggable.

- [ ] Create `app/plugins/` framework (BasePlugin, PluginRegistry)
- [ ] Refactor Warmane integration into a plugin
- [ ] Refactor Discord integration into a plugin
- [ ] Create plugin enable/disable API
- [ ] Build plugin management UI (guild settings)
- [ ] Create plugin developer documentation
- [ ] Frontend dynamic component loading for plugins
- [ ] **🧹 Phase 5 cleanup** (see [§13.3.6](#1336-phase-5-cleanup-checklist)):
  - [ ] Remove inline Warmane API calls from services — all go through plugin interface
  - [ ] Remove inline Discord integration from services — all go through plugin interface
  - [ ] Delete `src/api/warmane.js` if fully moved to plugin dynamic loading
  - [ ] Delete `src/api/armory.js` if fully moved to plugin dynamic loading
  - [ ] Remove hardcoded Warmane realm list if realms are now provider-agnostic
  - [ ] Clean up old import paths referencing moved modules
  - [ ] Run full lint + build + test suite on clean branch

### Phase 6: SaaS Infrastructure
**Goal:** Add billing and tenant management.

- [x] ~~Evaluate need for row-level tenancy (tenant_id enforcement)~~ → **Moved to Phase 0**
- [ ] Add subscription/billing model per tenant (free / pro / enterprise plans)
- [ ] Add usage tracking per tenant (guilds, members, events)
- [ ] Add API rate limiting per tenant
- [ ] Add data export/import for tenant portability
- [ ] Add tenant deletion with full data cleanup
- [ ] Add tenant suspension/reactivation by global admin
- [ ] **🧹 Phase 6 cleanup** (see [§13.3.7](#1337-phase-6-cleanup-checklist)):
  - [ ] Remove free-plan hardcoded defaults if plan limits now come from billing model
  - [ ] Remove any manual guild/member counting if usage tracking replaces it
  - [ ] Clean up Phase 0 `max_guilds`/`max_members` defaults if billing system overrides them
  - [ ] Final full-codebase dead-code audit (see §13.4)
  - [ ] Run full lint + build + test suite on clean branch

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
| 5 | Invitation expiry default? | 24h / 7d / 30d / Never | **7 days** with tenant/guild admin override |
| 6 | Allow users to see guilds they're not members of? | Yes (listed) / No (private) | **Configurable** per guild within the tenant (visibility setting) |
| 7 | Database name change from `wotlk_calendar.db`? | Yes / No | **Yes** — rename to `raid_calendar.db` or `guild_calendar.db` in a future phase |
| 8 | Should the `WowClass` Python enum remain? | Keep as universal / Replace with expansion-dynamic | **Keep as superset** of all classes; filter at runtime by expansion |
| 9 | Should the default expansion be a named constant? | Hardcoded / Constant | **Named constant** (`DEFAULT_EXPANSION = "wotlk"`) to avoid scattered magic strings |
| 10 | Default guild limit per tenant? | 1 / 3 / 5 / 10 | **3** for free plan, higher for paid plans (future) |
| 11 | Default member limit per tenant? | 25 / 50 / 100 / unlimited | **50** for free plan, higher for paid plans (future) |
| 12 | Should tenant invitations be shareable (multi-use) by default? | Single-use / Multi-use / Configurable | **Configurable** — single-use for security, multi-use for convenience, with expiry |
| 13 | How should tenant slug be generated? | From username / Custom / Auto-generated | **From username** at creation, customizable later |

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
| Tenant | manage_tenant_members | Invite/remove members from tenant |
| Tenant | manage_tenant_settings | Change tenant name, limits, settings |
| Guild | invite_members | Send guild invitations within tenant |
| Guild | approve_applications | Approve/decline membership applications |
| Guild | manage_guild_visibility | Change guild visibility within tenant |
| Guild | manage_class_role_matrix | Edit class-role assignment matrix |
| Guild | manage_guild_expansions | Enable/disable expansion packs for guild |
| Admin | manage_tenants | View/suspend/delete tenants (global admin) |
| Admin | manage_plugins | Enable/disable system plugins |

---

## 10. Phase 0: Per-User Tenancy — Detailed Plan

> **Priority:** This is the very first implementation step — before Phase 1
> (expansion registry), Phase 2 (guild membership), or any other feature work.
>
> **Why first?** Every subsequent phase adds more tables, queries, and features.
> If we retrofit `tenant_id` enforcement later, we must audit every new query
> written by Phases 1-6. Doing it now means all future code is written with
> tenant isolation baked in from day one, and debugging cross-tenant data leaks
> in a mature codebase is exponentially harder.
>
> **What is a tenant?** A per-user workspace. When a user registers, a `Tenant`
> is automatically created for them. They are the **owner** of that tenant. They
> can create guilds within it (up to a configurable limit), invite other players,
> and manage everything as if it were their own private application. Other users
> invited into the tenant become **tenant members** and can participate in guilds,
> events, signups, etc. within that tenant only.

---

### 10.1 What Is Per-User Row-Level Tenancy?

Row-level tenancy (also called "shared database, shared schema" multi-tenancy)
means **every tenant-scoped row** in the database carries a `tenant_id` foreign
key that identifies which tenant (user workspace) owns that data. Every query
that reads or writes tenant-scoped data **must** include a
`WHERE tenant_id = :tenant_id` filter.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           Single Database                                     │
│                                                                               │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐      │
│  │ Tenant A (User 1)  │  │ Tenant B (User 2)  │  │ Tenant C (User 3)  │     │
│  │ tenant_id = 1      │  │ tenant_id = 2      │  │ tenant_id = 3      │     │
│  │                    │  │                    │  │                    │      │
│  │ ┌──────────────┐  │  │ ┌──────────────┐  │  │ ┌──────────────┐  │      │
│  │ │ Guild A      │  │  │ │ Guild C      │  │  │ │ Guild E      │  │      │
│  │ │ Guild B      │  │  │ │ Guild D      │  │  │ │              │  │      │
│  │ └──────────────┘  │  │ └──────────────┘  │  │ └──────────────┘  │      │
│  │                    │  │                    │  │                    │      │
│  │ events, signups,   │  │ events, signups,   │  │ events, signups,   │     │
│  │ characters, etc.   │  │ characters, etc.   │  │ characters, etc.   │     │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘      │
│                                                                               │
│  User 4 is a MEMBER of Tenant A and Tenant B → switches via sidebar           │
│  User 1 is the OWNER of Tenant A → manages everything within it               │
│                                                                               │
│  Isolation enforced by WHERE tenant_id = ? on EVERY query                     │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ GLOBAL (no tenant_id): users, system_settings, permissions,            │  │
│  │   system_roles, role_permissions, role_grant_rules, job_queue           │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 How It Behaves for the User

> "Each user should have their own application, but in my database and without
> being a global admin."

| User Role | What They See | What They Can Do |
|-----------|--------------|------------------|
| **Tenant Owner** | Their own workspace with guilds, events, members | Create guilds (up to plan limit), invite players, manage everything within their tenant. Full admin of their workspace. |
| **Tenant Member** (invited) | The workspace they were invited to; can switch between multiple tenants via sidebar | Participate in guilds, sign up for events, manage their characters — all within the active tenant context. Cannot create new guilds (unless given admin role in tenant). |
| **Multi-Tenant User** | Sidebar shows all tenants they belong to | Switch tenants in real time. Each switch changes the data context entirely — different guilds, events, characters. |
| **Global Admin** | Global admin panel with "Tenants" tab | View all tenants, suspend/activate tenants, override limits, manage platform-wide settings. Does NOT need to be a member of a tenant to manage it. |

### 10.3 Risks & Mitigation

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| 1 | **Cross-tenant data leak** — forgetting `tenant_id` filter exposes Tenant A's data to Tenant B | 🔴 Critical | High (many queries) | `TenantMixin` base class + integration tests per endpoint |
| 2 | **Data migration corruption** — backfilling `tenant_id` on existing rows uses wrong parent chain | 🔴 Critical | Medium | Run migration on a copy first; write verification queries; compare row counts |
| 3 | **Performance regression** — adding `tenant_id` column + index to every table | 🟡 Medium | Low | Composite indexes `(tenant_id, <existing_index>)` replace single-column indexes |
| 4 | **Broken unique constraints** — existing constraints may need `tenant_id` added | 🟡 Medium | Medium | Audit every constraint; guild-scoped constraints stay as-is (guild already belongs to one tenant) |
| 5 | **Tenant switching complexity** — frontend state management for multi-tenant switching | 🟡 Medium | Medium | Active tenant stored in auth store (Pinia); switching triggers full data reload |
| 6 | **Invitation token security** — brute-force or leaked invite links | 🟡 Medium | Low | Cryptographically random 64-char tokens; optional expiry; rate limiting |
| 7 | **Test suite breakage** — all 632+ tests assume current schema | 🟡 Medium | High | Run full suite after each table migration; fix tests incrementally |
| 8 | **Global admin queries break** — admin dashboard counts should NOT be tenant-filtered | 🟡 Medium | Medium | Clearly separate global-scoped tables/queries from tenant-scoped ones |
| 9 | **Seed data duplication** — system-wide seeds (permissions, roles, default raid definitions) must remain `tenant_id=NULL` | 🟢 Low | Low | Only tenant-scoped tables get `NOT NULL` constraint; system tables keep absent |
| 10 | **Auto-create tenant on registration** — race conditions or failures | 🟢 Low | Low | Wrap registration + tenant creation in a single DB transaction |

### 10.4 Table Classification: Global vs. Tenant-Scoped

Every table in the application falls into one of three categories:

| Category | Tables | `tenant_id` needed? | Rationale |
|----------|--------|-------------------|-----------|
| **Global (system-wide)** | `users`, `system_settings`, `permissions`, `system_roles`, `role_permissions`, `role_grant_rules`, `job_queue` | ❌ No | Shared across all tenants. Users exist globally (can belong to multiple tenants). Permissions/roles are system-wide definitions. |
| **New tenant tables** | `tenants`, `tenant_memberships`, `tenant_invitations` | N/A (these define tenancy) | These ARE the tenant infrastructure. |
| **Tenant-scoped** | `guilds`, `guild_memberships`, `guild_features`, `characters`, `raid_definitions`, `raid_templates`, `event_series`, `raid_events`, `signups`, `lineup_slots`, `raid_bans`, `attendance_records`, `character_replacements`, `notifications` | ✅ Must have `tenant_id` | All guild-related data is owned by a tenant. |
| **User-scoped (not tenant)** | `armory_configs` | ❌ No | User-scoped personal config, not tenant-specific. Guild links via `Guild.armory_config_id` FK. |

### 10.5 New Models

#### 10.5.1 `Tenant` Model

```python
# app/models/tenant.py (NEW FILE)

class Tenant(db.Model):
    """Per-user workspace — the top-level isolation boundary.
    Auto-created when a user registers. The owner has full control."""

    __tablename__ = "tenants"

    id            = Column(Integer, primary_key=True)
    name          = Column(String(100), nullable=False)
    slug          = Column(String(100), unique=True, nullable=False)
    owner_id      = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    plan          = Column(String(30), default="free")      # free / pro / enterprise
    max_guilds    = Column(Integer, default=3)               # guild limit per plan
    max_members   = Column(Integer, default=50)              # member limit per plan
    is_active     = Column(Boolean, default=True)            # global admin can suspend
    settings_json = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=utcnow)
    updated_at    = Column(DateTime, default=utcnow, onupdate=utcnow)

    owner       = relationship("User", foreign_keys=[owner_id], backref="owned_tenant")
    memberships = relationship("TenantMembership", back_populates="tenant", cascade="all, delete-orphan")
    guilds      = relationship("Guild", back_populates="tenant", cascade="all, delete-orphan")
```

#### 10.5.2 `TenantMembership` Model

```python
class TenantMembership(db.Model):
    """Links a user to a tenant. Owner always has role='owner'.
    Invited users get 'member' or 'admin'."""

    __tablename__ = "tenant_memberships"

    id         = Column(Integer, primary_key=True)
    tenant_id  = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    role       = Column(String(30), default="member")  # owner / admin / member
    status     = Column(Enum(MemberStatus), default=MemberStatus.ACTIVE)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )

    tenant = relationship("Tenant", back_populates="memberships")
    user   = relationship("User", backref="tenant_memberships")
```

#### 10.5.3 `TenantInvitation` Model

```python
class TenantInvitation(db.Model):
    """Invitation to join a tenant workspace.
    Supports shareable links, Discord OAuth, and direct in-app invites."""

    __tablename__ = "tenant_invitations"

    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    inviter_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    invitee_email   = Column(String(255), nullable=True)
    invitee_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    invite_token    = Column(String(64), unique=True, nullable=False)
    role            = Column(String(30), default="member")
    status          = Column(String(20), default="pending")  # pending/accepted/declined/expired
    max_uses        = Column(Integer, nullable=True)         # NULL = unlimited uses
    use_count       = Column(Integer, default=0)
    expires_at      = Column(DateTime, nullable=True)        # NULL = never expires
    created_at      = Column(DateTime, default=utcnow)
    accepted_at     = Column(DateTime, nullable=True)

    tenant  = relationship("Tenant")
    inviter = relationship("User", foreign_keys=[inviter_id])
    invitee = relationship("User", foreign_keys=[invitee_user_id])
```

### 10.6 Table-by-Table Change Plan

#### 10.6.1 `guilds` — Add `tenant_id`

Currently, guilds exist in a flat namespace. After this change, every guild
belongs to exactly one tenant.

**Model change (`app/models/guild.py`):**
```python
# Add to Guild class:
tenant_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True
)

tenant = relationship("Tenant", back_populates="guilds", lazy="select")
```

**Index changes:**
```python
# Add to __table_args__:
sa.Index("ix_guilds_tenant", "tenant_id"),
sa.Index("ix_guilds_tenant_name", "tenant_id", "name"),  # For name uniqueness within tenant
```

**Data migration (SQL):**
```sql
-- Step 1: Create a tenant for each user who owns a guild
INSERT INTO tenants (name, slug, owner_id, created_at)
SELECT
    u.username || '''s Workspace',
    u.username,
    u.id,
    u.created_at
FROM users u
WHERE u.id IN (SELECT DISTINCT created_by FROM guilds WHERE created_by IS NOT NULL);

-- Step 2: Create a tenant for users who don't own guilds (every user gets a tenant)
INSERT INTO tenants (name, slug, owner_id, created_at)
SELECT
    u.username || '''s Workspace',
    u.username,
    u.id,
    u.created_at
FROM users u
WHERE u.id NOT IN (SELECT owner_id FROM tenants);

-- Step 3: Create owner memberships
INSERT INTO tenant_memberships (tenant_id, user_id, role, status, created_at)
SELECT t.id, t.owner_id, 'owner', 'active', t.created_at
FROM tenants t;

-- Step 4: Backfill guild.tenant_id from the owner's tenant
UPDATE guilds SET tenant_id = (
    SELECT t.id FROM tenants t WHERE t.owner_id = guilds.created_by
);

-- Step 5: Create tenant memberships for all guild members who aren't already tenant members
INSERT INTO tenant_memberships (tenant_id, user_id, role, status, created_at)
SELECT DISTINCT g.tenant_id, gm.user_id, 'member', 'active', gm.created_at
FROM guild_memberships gm
JOIN guilds g ON g.id = gm.guild_id
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_memberships tm
    WHERE tm.tenant_id = g.tenant_id AND tm.user_id = gm.user_id
);
```

#### 10.6.2 Tables That Already Have `guild_id` — Add `tenant_id`

These tables already have `guild_id` but need `tenant_id` as the primary tenant
isolation column. The `guild_id` remains for guild-level scoping within a tenant.

**Tables to update:**

| Table | Current `guild_id` | `tenant_id` action |
|-------|-------------------|-------------------|
| `guild_memberships` | ✅ Has `guild_id` | Add `tenant_id` (backfill from `guilds.tenant_id`) |
| `guild_features` | ✅ Has `guild_id` | Add `tenant_id` (backfill from `guilds.tenant_id`) |
| `characters` | ✅ Has `guild_id` | Add `tenant_id` (backfill from `guilds.tenant_id`) |
| `raid_definitions` | ✅ Has `guild_id` (nullable) | Add `tenant_id` (nullable — `NULL` = builtin/default) |
| `raid_templates` | ✅ Has `guild_id` | Add `tenant_id` (backfill from `guilds.tenant_id`) |
| `event_series` | ✅ Has `guild_id` | Add `tenant_id` (backfill from `guilds.tenant_id`) |
| `raid_events` | ✅ Has `guild_id` | Add `tenant_id` (backfill from `guilds.tenant_id`) |
| `notifications` | ✅ Has `guild_id` (nullable) | Add `tenant_id` (nullable — some notifications are system-wide) |

**Generic model change pattern:**
```python
# For each model above, add:
tenant_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True
)

tenant = relationship("Tenant", foreign_keys=[tenant_id], lazy="select")
```

**Generic backfill pattern:**
```sql
-- For tables with guild_id → guilds.tenant_id
UPDATE {table} SET tenant_id = (
    SELECT guilds.tenant_id FROM guilds WHERE guilds.id = {table}.guild_id
);
```

#### 10.6.3 Tables That Need Both `tenant_id` AND `guild_id` Added

These tables currently rely on a FK chain to determine tenant ownership
(e.g., `signup → raid_event → guild → tenant`). Adding direct `tenant_id` and
`guild_id` columns allows:
1. Direct tenant-scoped queries without JOINs
2. Safety — even if a bug corrupts a parent FK, the tenant boundary holds
3. Future index optimization

| Table | Current FK chain | Add columns |
|-------|-----------------|-------------|
| `signups` | `signup → raid_event → guild → tenant` | `tenant_id` + `guild_id` |
| `lineup_slots` | `slot → raid_event → guild → tenant` | `tenant_id` + `guild_id` |
| `raid_bans` | `ban → raid_event → guild → tenant` | `tenant_id` + `guild_id` |
| `attendance_records` | `record → raid_event → guild → tenant` | `tenant_id` + `guild_id` |
| `character_replacements` | `replacement → signup → raid_event → guild → tenant` | `tenant_id` + `guild_id` |

**Model change example (`Signup`):**
```python
# Add to Signup class:
tenant_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True
)
guild_id: Mapped[int] = mapped_column(
    sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True
)

tenant = relationship("Tenant", foreign_keys=[tenant_id], lazy="select")
guild  = relationship("Guild", foreign_keys=[guild_id], lazy="select")
```

**Backfill for these tables:**
```sql
-- signups → raid_events → guilds
UPDATE signups SET
    guild_id = (SELECT re.guild_id FROM raid_events re WHERE re.id = signups.raid_event_id),
    tenant_id = (SELECT g.tenant_id FROM raid_events re JOIN guilds g ON g.id = re.guild_id WHERE re.id = signups.raid_event_id);

-- lineup_slots → raid_events → guilds
UPDATE lineup_slots SET
    guild_id = (SELECT re.guild_id FROM raid_events re WHERE re.id = lineup_slots.raid_event_id),
    tenant_id = (SELECT g.tenant_id FROM raid_events re JOIN guilds g ON g.id = re.guild_id WHERE re.id = lineup_slots.raid_event_id);

-- raid_bans → raid_events → guilds
UPDATE raid_bans SET
    guild_id = (SELECT re.guild_id FROM raid_events re WHERE re.id = raid_bans.raid_event_id),
    tenant_id = (SELECT g.tenant_id FROM raid_events re JOIN guilds g ON g.id = re.guild_id WHERE re.id = raid_bans.raid_event_id);

-- attendance_records → raid_events → guilds
UPDATE attendance_records SET
    guild_id = (SELECT re.guild_id FROM raid_events re WHERE re.id = attendance_records.raid_event_id),
    tenant_id = (SELECT g.tenant_id FROM raid_events re JOIN guilds g ON g.id = re.guild_id WHERE re.id = attendance_records.raid_event_id);

-- character_replacements → signups → raid_events → guilds (2-hop)
UPDATE character_replacements SET
    guild_id = (SELECT re.guild_id FROM signups s JOIN raid_events re ON re.id = s.raid_event_id WHERE s.id = character_replacements.signup_id),
    tenant_id = (SELECT g.tenant_id FROM signups s JOIN raid_events re ON re.id = s.raid_event_id JOIN guilds g ON g.id = re.guild_id WHERE s.id = character_replacements.signup_id);
```

### 10.7 `TenantMixin` — Reusable Base Class

```python
# app/models/mixins.py (NEW FILE)

class TenantMixin:
    """Mixin for models that are scoped to a tenant (user workspace).

    Adds tenant_id FK and provides helper methods for tenant-scoped queries.
    """

    @declared_attr
    def tenant_id(cls):
        return mapped_column(
            sa.Integer,
            sa.ForeignKey("tenants.id"),
            nullable=False,
            index=True,
        )

    @declared_attr
    def tenant(cls):
        return relationship("Tenant", foreign_keys=[cls.tenant_id], lazy="select")

    @classmethod
    def tenant_query(cls, tenant_id: int):
        """Return a base query filtered by tenant_id."""
        return sa.select(cls).where(cls.tenant_id == tenant_id)

    @classmethod
    def tenant_filter(cls, tenant_id: int):
        """Return a WHERE clause for tenant_id filtering."""
        return cls.tenant_id == tenant_id
```

**Usage in models:**
```python
class Guild(TenantMixin, db.Model):
    # tenant_id and tenant relationship are inherited from TenantMixin
    ...

class Signup(TenantMixin, db.Model):
    # tenant_id inherited; also has guild_id for guild-level scoping
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False, index=True)
    ...
```

**Usage in services:**
```python
# Before:
stmt = sa.select(Guild)

# After:
stmt = sa.select(Guild).where(Guild.tenant_id == tenant_id)

# Or using helper:
stmt = Guild.tenant_query(tenant_id)
```

### 10.8 Service Layer — Complete Query Audit

Every service file that performs database queries must be audited for tenant
isolation. Below is the complete list of changes needed per file.

#### `app/services/guild_service.py` (~12 queries)

| # | Function | Current | Change |
|---|----------|---------|--------|
| 1 | `create_guild()` | No tenant check | Set `guild.tenant_id = tenant_id`; check guild count vs. `tenant.max_guilds` |
| 2 | `list_guilds()` | Lists user's guilds | Add `.where(Guild.tenant_id == tenant_id)` |
| 3 | `list_all_guilds()` | Returns ALL guilds | Add `.where(Guild.tenant_id == tenant_id)` |
| 4 | `get_guild()` | By PK | Add `tenant_id` ownership check after fetch |
| 5 | `update_guild()` | By object | Caller verifies `tenant_id` (via membership check) |
| 6 | `delete_guild()` | By object | Caller verifies `tenant_id` |
| 7 | `list_members()` | By guild_id | Add `tenant_id` filter |
| 8 | `add_member()` | By guild_id + user_id | Verify user is a tenant member before adding to guild |
| 9 | `remove_member()` | By object | Caller verifies `tenant_id` |
| 10 | `get_membership()` | By guild_id + user_id | Add `tenant_id` filter |

#### `app/services/event_service.py` (~30 queries)

| # | Function | Change |
|---|----------|--------|
| 1 | `get_template()` | Add `tenant_id` ownership check after `db.session.get()` |
| 2 | `get_event()` | Add `tenant_id` ownership check after `db.session.get()` |
| 3 | `get_series()` | Add `tenant_id` ownership check after `db.session.get()` |
| 4 | `list_events()` | Add `.where(RaidEvent.tenant_id == tenant_id)` |
| 5 | `list_events_for_guilds()` | Add `tenant_id` filter |
| 6 | `list_events_for_guilds_by_range()` | Add `tenant_id` filter |
| 7 | `copy_template_to_guild()` | Verify both source and target guild belong to same tenant |
| 8 | `copy_series_to_guild()` | Same cross-tenant safety check |
| 9 | `duplicate_event()` | Set `tenant_id` on new event |
| 10 | All `list_*()` functions | Already filter by `guild_id` — also add `tenant_id` |

#### `app/services/signup_service.py` (~20 queries)

| # | Function | Change |
|---|----------|--------|
| 1 | `create_signup()` | Set `signup.tenant_id = tenant_id` and `signup.guild_id = guild_id` |
| 2 | `get_signup()` | Add `tenant_id` ownership check |
| 3 | `list_signups()` | Add `.where(Signup.tenant_id == tenant_id)` |
| 4 | `list_user_signups()` | Add `.where(Signup.tenant_id == tenant_id)` |
| 5 | `create_ban()` | Set `ban.tenant_id` and `ban.guild_id` |
| 6 | `get_ban()` | Add `tenant_id` filter |
| 7 | `list_bans()` | Add `tenant_id` filter |
| 8 | `request_replacement()` | Add `tenant_id` filter; set on new object |
| 9 | `confirm_replacement()` | Add `tenant_id` to all sub-queries |
| 10 | All internal helpers (`_check_character_ownership`, `_count_*`) | Add `tenant_id` context |

#### `app/services/lineup_service.py` (~25 queries)

| # | Function | Change |
|---|----------|--------|
| 1 | `get_lineup()` | Add `tenant_id` filter |
| 2 | `add_slot()` | Set `slot.tenant_id`; add to max query |
| 3 | `remove_slot()` | Add `tenant_id` filter |
| 4 | `save_full_lineup()` | Set `tenant_id` on every new `LineupSlot`; add filter on delete |
| 5 | `reorder_bench()` | Add `tenant_id` filter to all queries |
| 6 | `confirm_lineup()` | `tenant_id` passed via `get_lineup()` |

#### `app/services/attendance_service.py` (~5 queries)

| # | Function | Change |
|---|----------|--------|
| 1 | `record_attendance()` | Set `tenant_id` on record; add to query |
| 2 | `get_event_attendance()` | Add `tenant_id` filter |
| 3 | `list_attendance_for_guild()` | Add `tenant_id` filter |

#### `app/services/character_service.py` (~10 queries)

| # | Function | Change |
|---|----------|--------|
| 1 | `get_character()` | Add `tenant_id` ownership check |
| 2 | `list_characters()` | Add `tenant_id` filter (or verify via guild) |
| 3 | `create_character()` | Set `tenant_id` from guild's tenant |
| 4 | `find_existing_character()` | Add `tenant_id` filter |

#### `app/services/raid_service.py` (~8 queries)

| # | Function | Change |
|---|----------|--------|
| 1 | `get_raid_definition()` | Add `tenant_id` ownership check |
| 2 | `list_raid_definitions()` | Add `tenant_id` filter (or `tenant_id IS NULL` for builtins) |
| 3 | `copy_raid_definition_to_guild()` | Verify tenant match |

#### `app/services/notification_service.py` (~8 queries)

Notifications are **user-scoped** with optional `tenant_id` context. Current
queries filter by `user_id` which is correct. Add optional `tenant_id` filtering
for "show notifications from this tenant only" feature. ✅

#### Other services (no changes needed)

| Service | Reason |
|---------|--------|
| `auth_service.py` | Global/user-scoped queries ✅ |
| `feature_service.py` | Already filters by `guild_id` — add `tenant_id` as additional filter |
| `discord_service.py` | Global/user-scoped ✅ |
| `warmane_service.py` | External API, no DB ✅ |

### 10.9 API Layer — Route Changes

#### 10.9.1 New Tenant Routes

```python
# app/api/v1/tenants.py (NEW BLUEPRINT)

# Tenant CRUD (for tenant owners):
GET    /api/v1/tenants                           # List user's tenants (owned + member)
GET    /api/v1/tenants/<int:tenant_id>            # Get tenant details
PUT    /api/v1/tenants/<int:tenant_id>            # Update tenant settings
DELETE /api/v1/tenants/<int:tenant_id>            # Delete tenant (owner only)

# Tenant members:
GET    /api/v1/tenants/<int:tenant_id>/members                    # List members
POST   /api/v1/tenants/<int:tenant_id>/members                    # Add member directly
PUT    /api/v1/tenants/<int:tenant_id>/members/<int:user_id>      # Update member role
DELETE /api/v1/tenants/<int:tenant_id>/members/<int:user_id>      # Remove member

# Tenant invitations:
GET    /api/v1/tenants/<int:tenant_id>/invitations                # List invitations
POST   /api/v1/tenants/<int:tenant_id>/invitations                # Create invite (link/discord/direct)
DELETE /api/v1/tenants/<int:tenant_id>/invitations/<int:inv_id>   # Revoke invitation
POST   /api/v1/invite/<token>                                     # Accept invite (public endpoint)

# Tenant switching:
PUT    /api/v1/auth/active-tenant                                 # Switch active tenant
GET    /api/v1/auth/active-tenant                                 # Get current active tenant
```

#### 10.9.2 Existing Routes — Add `tenant_id` Context

All existing guild-scoped routes already use `<int:guild_id>` in the URL. The
`tenant_id` will be resolved from:
1. The user's **active tenant** (stored in session or JWT claims)
2. Verified against the guild's `tenant_id` on every request

```python
# In the guild permission decorator:
def require_guild_permission(permission_code):
    def decorator(f):
        @wraps(f)
        def wrapper(guild_id, *args, **kwargs):
            user = get_current_user()
            guild = Guild.query.get_or_404(guild_id)

            # NEW: Verify guild belongs to user's active tenant
            if guild.tenant_id != user.active_tenant_id:
                abort(404)  # Don't reveal existence of guilds in other tenants

            membership = get_membership(guild_id, user.id)
            if not membership:
                abort(403)
            if not has_permission(membership, permission_code):
                abort(403)

            return f(guild_id=guild_id, membership=membership, *args, **kwargs)
        return wrapper
    return decorator
```

#### 10.9.3 Admin Routes — Tenant Management

```python
# app/api/v1/admin.py — New endpoints:

GET    /api/v1/admin/tenants                                      # List all tenants (with stats)
GET    /api/v1/admin/tenants/<int:tenant_id>                      # Get tenant details
PUT    /api/v1/admin/tenants/<int:tenant_id>                      # Update tenant (limits, plan)
POST   /api/v1/admin/tenants/<int:tenant_id>/suspend              # Suspend tenant
POST   /api/v1/admin/tenants/<int:tenant_id>/activate             # Reactivate tenant
DELETE /api/v1/admin/tenants/<int:tenant_id>                      # Delete tenant + all data
PUT    /api/v1/admin/tenants/<int:tenant_id>/limits               # Override guild/member limits
```

### 10.10 Frontend Changes

#### 10.10.1 Tenant Switching — Sidebar Component

Users who belong to multiple tenants see a tenant switcher in the sidebar:

```
┌─────────────────────────────────────────┐
│  ┌─────────────────────────────────────┐│
│  │ 🏠 Active Tenant                    ││
│  │ ┌─────────────────────────────────┐ ││
│  │ │ ▼ Arthas's Workspace        ✓  │ ││
│  │ │   Thrall's Guild Hub            │ ││
│  │ │   PvP League (invited)          │ ││
│  │ └─────────────────────────────────┘ ││
│  └─────────────────────────────────────┘│
│                                         │
│  📅 Calendar                            │
│  ⚔️ Guilds                              │
│  👤 Characters                          │
│  🔔 Notifications                       │
│  ⚙️ Settings                            │
│                                         │
│  ─────────────────────────              │
│  🔧 Tenant Settings (owner only)       │
│  👥 Invite Players                      │
│  🛡️ Global Admin (if admin)            │
└─────────────────────────────────────────┘
```

**Behavior on tenant switch:**
1. User clicks a different tenant in the dropdown
2. Frontend calls `PUT /api/v1/auth/active-tenant` with new `tenant_id`
3. Server validates user is a member of that tenant
4. Server updates session/JWT with new active tenant
5. Frontend reloads guild store, calendar store, character store
6. All subsequent API calls are scoped to the new tenant

#### 10.10.2 Auth Store Changes (`src/stores/auth.js`)

```javascript
// Add to auth store state:
{
    user: { ... },
    activeTenantId: null,        // Currently active tenant
    tenants: [],                 // All tenants user belongs to (owned + member)
}

// New actions:
async fetchTenants() {
    const { data } = await api.get('/tenants')
    this.tenants = data
    if (!this.activeTenantId && data.length > 0) {
        this.activeTenantId = data[0].id  // Default to first tenant (owned)
    }
}

async switchTenant(tenantId) {
    await api.put('/auth/active-tenant', { tenant_id: tenantId })
    this.activeTenantId = tenantId
    // Trigger reload of guild, calendar, character stores
    await guildStore.fetchGuilds()
    await calendarStore.reset()
}
```

#### 10.10.3 User Model Changes (`app/models/user.py`)

```python
# Add to User model:
active_tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

# Relationship:
active_tenant = relationship("Tenant", foreign_keys=[active_tenant_id])
```

#### 10.10.4 Registration Flow Changes (`app/services/auth_service.py`)

```python
def register_user(email, username, password):
    """Register a new user and auto-create their tenant."""
    user = User(email=email, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # Get user.id

    # Auto-create tenant for the new user
    # Note: slug generation should use a robust slugify function that handles
    # Unicode, special characters, and appends a unique suffix on collision.
    # Simplified here for illustration.
    tenant = Tenant(
        name=f"{username}'s Workspace",
        slug=generate_unique_slug(username),  # e.g., "arthas" or "arthas-2" on collision
        owner_id=user.id,
        plan="free",
        max_guilds=3,
        max_members=50,
    )
    db.session.add(tenant)
    db.session.flush()  # Get tenant.id

    # Create owner membership
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role="owner",
        status=MemberStatus.ACTIVE,
    )
    db.session.add(membership)

    # Set as active tenant
    user.active_tenant_id = tenant.id

    db.session.commit()
    return user
```

#### 10.10.5 Global Admin Panel — Tenants Tab

Add a new `TenantsTab` component to `GlobalAdminView`:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Global Admin Panel                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Dashboard │ Users │ Roles │ Tenants │ Guilds │ Raids │ Settings ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─ Tenants ──────────────────────────────────────────────────────┐  │
│  │ ID │ Name              │ Owner    │ Plan │ Guilds │ Members │  │  │
│  │ 1  │ Arthas's Workspace│ arthas   │ free │ 2/3   │ 15/50  │  │  │
│  │ 2  │ Thrall's Hub      │ thrall   │ pro  │ 5/10  │ 42/200 │  │  │
│  │ 3  │ PvP League        │ sylvanas │ free │ 1/3   │ 8/50   │  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Actions: View Details │ Edit Limits │ Suspend │ Delete               │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.11 Invitation System — Detailed Design

#### 10.11.1 Shareable Invite Link

```
Flow:
1. Tenant owner/admin generates invite link
2. System creates TenantInvitation with:
   - invite_token = crypto.randomBytes(32).toString('hex')
   - max_uses = null (unlimited) or N (single/multi-use)
   - expires_at = null (never) or DateTime
3. Frontend shows copyable link: https://app.example.com/invite/{token}
4. Invitee clicks link:
   - If logged in: show "Join {tenant_name}?" confirmation → accept/decline
   - If not logged in: redirect to register/login → then auto-join
5. On accept: create TenantMembership with role from invitation
```

#### 10.11.2 Discord OAuth Invite

```
Flow:
1. Tenant owner connects Discord bot to their Discord server (one-time setup)
2. Owner generates a Discord-linked invite from the UI
3. System sends a Discord DM or posts in a channel:
   "You've been invited to {tenant_name}! Click here: {invite_link}"
4. Player clicks the link → redirected to app with Discord OAuth
5. If player has an account linked to Discord → auto-join tenant
6. If not → complete Discord-linked registration → auto-join tenant
```

#### 10.11.3 Direct In-App Invite

```
Flow:
1. Tenant owner searches for existing users by username
2. System creates TenantInvitation with invitee_user_id set
3. Invitee receives an in-app notification:
   "{owner} invited you to {tenant_name} — Accept / Decline"
4. Invitee accepts from notification panel → TenantMembership created
```

### 10.12 Utility Layer — Query Audit

#### `app/utils/permissions.py`

| Function | Status | Change |
|----------|--------|--------|
| `get_membership()` | Uses `guild_id` + `user_id` | Add `tenant_id` pre-check: verify guild belongs to active tenant |
| `has_permission()` | Uses membership | No change — operates on membership object |
| `has_any_guild_permission()` | Cross-guild query | Scope to active tenant's guilds |
| `get_user_permissions()` | Uses membership role | No change |

#### `app/utils/api_helpers.py`

| Function | Status | Change |
|----------|--------|--------|
| `get_event_or_404()` | Checks `event.guild_id == guild_id` | Also check `event.tenant_id == active_tenant_id` |
| `build_guild_role_map()` | Filters by `guild_id` | Add `tenant_id` filter |

#### `app/utils/decorators.py`

| Function | Change |
|----------|--------|
| `guild_permission_required()` | Add `tenant_id` check: guild must belong to user's active tenant |

#### `app/utils/notify.py`

| Function | Change |
|----------|--------|
| `_get_officer_user_ids()` | Add `tenant_id` context |
| `_guild_member_ids()` | Add `tenant_id` context |

### 10.13 Background Jobs — Query Audit

| Job | Status | Change |
|-----|--------|--------|
| `handle_send_notification()` | `tenant_id` from payload | No change — uses `guild_id` from payload ✅ (add `tenant_id` to payload) |
| `auto_lock_upcoming_events()` | Global scheduler | No change — intentionally cross-tenant for system scheduler ✅ |
| `handle_sync_characters()` | Optional `guild_id` filter | Add optional `tenant_id` filter for per-tenant sync |

### 10.14 Database Migration — Step-by-Step

The migration must be executed as a **single Alembic migration** to maintain
atomicity. Here is the exact sequence:

```python
# migrations/versions/xxxx_add_per_user_tenancy.py

def upgrade():
    # ── Step 1: Create new tenant tables ──
    op.create_table('tenants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('plan', sa.String(30), server_default='free'),
        sa.Column('max_guilds', sa.Integer(), server_default='3'),
        sa.Column('max_members', sa.Integer(), server_default='50'),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('settings_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table('tenant_memberships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(30), server_default='member'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user'),
    )

    op.create_table('tenant_invitations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('inviter_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('invitee_email', sa.String(255), nullable=True),
        sa.Column('invitee_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('invite_token', sa.String(64), unique=True, nullable=False),
        sa.Column('role', sa.String(30), server_default='member'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('use_count', sa.Integer(), server_default='0'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
    )

    # ── Step 2: Add active_tenant_id to users ──
    op.add_column('users', sa.Column('active_tenant_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_active_tenant', 'users', 'tenants', ['active_tenant_id'], ['id'])

    # ── Step 3: Add tenant_id to tenant-scoped tables (nullable initially for backfill) ──
    tenant_scoped_tables = [
        'guilds', 'guild_memberships', 'guild_features',
        'characters', 'raid_definitions', 'raid_templates',
        'event_series', 'raid_events', 'notifications',
    ]
    for table in tenant_scoped_tables:
        op.add_column(table, sa.Column('tenant_id', sa.Integer(), nullable=True))

    # Tables that also need guild_id:
    needs_guild_id = [
        'signups', 'lineup_slots', 'raid_bans',
        'attendance_records', 'character_replacements',
    ]
    for table in needs_guild_id:
        op.add_column(table, sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.add_column(table, sa.Column('guild_id', sa.Integer(), nullable=True))

    # ── Step 4: Backfill (see §10.6 for SQL) ──
    # 4a: Create tenants for all users
    # 4b: Create owner memberships
    # 4c: Backfill tenant_id on guilds from owner's tenant
    # 4d: Backfill tenant_id on guild-child tables from guilds.tenant_id
    # 4e: Backfill guild_id + tenant_id on event-child tables
    # 4f: Create tenant memberships for existing guild members
    # (SQL statements from §10.6)

    # ── Step 5: Make columns NOT NULL ──
    for table in tenant_scoped_tables:
        nullable = table in ('raid_definitions', 'notifications')  # keep nullable
        if not nullable:
            op.alter_column(table, 'tenant_id', nullable=False)
    for table in needs_guild_id:
        op.alter_column(table, 'tenant_id', nullable=False)
        op.alter_column(table, 'guild_id', nullable=False)

    # ── Step 6: Add foreign keys ──
    for table in tenant_scoped_tables + needs_guild_id:
        op.create_foreign_key(f'fk_{table}_tenant', table, 'tenants', ['tenant_id'], ['id'])
    for table in needs_guild_id:
        op.create_foreign_key(f'fk_{table}_guild', table, 'guilds', ['guild_id'], ['id'])

    # ── Step 7: Add indexes ──
    for table in tenant_scoped_tables + needs_guild_id:
        op.create_index(f'ix_{table}_tenant', table, ['tenant_id'])
    for table in needs_guild_id:
        op.create_index(f'ix_{table}_guild', table, ['guild_id'])


def downgrade():
    # Remove indexes, FKs, columns, then drop tenant tables
    # (reverse of upgrade steps)
    ...
```

### 10.15 Verification & Testing Plan

#### Pre-migration verification:
```sql
-- Count rows in each table BEFORE migration
SELECT 'guilds' AS tbl, COUNT(*) AS cnt FROM guilds
UNION ALL SELECT 'characters', COUNT(*) FROM characters
UNION ALL SELECT 'raid_events', COUNT(*) FROM raid_events
UNION ALL SELECT 'signups', COUNT(*) FROM signups
UNION ALL SELECT 'lineup_slots', COUNT(*) FROM lineup_slots
UNION ALL SELECT 'raid_bans', COUNT(*) FROM raid_bans
UNION ALL SELECT 'attendance_records', COUNT(*) FROM attendance_records
UNION ALL SELECT 'character_replacements', COUNT(*) FROM character_replacements;
```

#### Post-migration verification:
```sql
-- Verify NO nulls remain after backfill
SELECT 'guilds' AS tbl, COUNT(*) AS nulls FROM guilds WHERE tenant_id IS NULL
UNION ALL SELECT 'signups', COUNT(*) FROM signups WHERE tenant_id IS NULL OR guild_id IS NULL
UNION ALL SELECT 'lineup_slots', COUNT(*) FROM lineup_slots WHERE tenant_id IS NULL OR guild_id IS NULL
UNION ALL SELECT 'raid_bans', COUNT(*) FROM raid_bans WHERE tenant_id IS NULL OR guild_id IS NULL
UNION ALL SELECT 'attendance_records', COUNT(*) FROM attendance_records WHERE tenant_id IS NULL OR guild_id IS NULL;

-- Verify every user has a tenant
SELECT COUNT(*) AS users_without_tenant
FROM users u
WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.owner_id = u.id);
-- Expected: 0

-- Verify tenant_id consistency through parent chain
SELECT COUNT(*) AS mismatches
FROM guilds g
JOIN tenants t ON t.id = g.tenant_id
WHERE t.owner_id != g.created_by;
-- Expected: 0 (guild's tenant matches guild creator's tenant)

SELECT COUNT(*) AS mismatches
FROM signups s
JOIN raid_events re ON re.id = s.raid_event_id
WHERE s.tenant_id != re.tenant_id OR s.guild_id != re.guild_id;
-- Expected: 0
```

#### New integration tests:

```python
# tests/test_tenant_isolation.py (NEW FILE)

class TestTenantIsolation:
    """Verify that tenant-scoped data is properly isolated between tenants."""

    def test_user_registration_creates_tenant(self):
        """Registering a new user auto-creates a tenant with owner membership."""

    def test_tenant_owner_can_create_guilds(self):
        """Tenant owner can create guilds up to the plan limit."""

    def test_guild_creation_respects_tenant_limit(self):
        """Creating guilds beyond max_guilds is rejected."""

    def test_guild_data_isolated_between_tenants(self):
        """Guilds from Tenant A must NOT appear in Tenant B queries."""

    def test_event_data_isolated_between_tenants(self):
        """Events from Tenant A must NOT appear in Tenant B queries."""

    def test_signup_data_isolated_between_tenants(self):
        """Signups from Tenant A must NOT appear in Tenant B queries."""

    def test_character_data_isolated_between_tenants(self):
        """Characters from Tenant A must NOT appear in Tenant B queries."""

    def test_tenant_switching_changes_data_context(self):
        """User in Tenant A+B sees different guilds when switching tenants."""

    def test_invite_link_creates_tenant_membership(self):
        """Accepting an invite link creates a TenantMembership."""

    def test_invite_link_expired_rejected(self):
        """Expired invite links are rejected."""

    def test_invite_link_max_uses_enforced(self):
        """Multi-use invite links stop working after max_uses reached."""

    def test_tenant_member_cannot_see_other_tenant_guilds(self):
        """A member of Tenant A cannot access Tenant B's guilds."""

    def test_admin_can_see_all_tenants(self):
        """Global admin dashboard shows ALL tenants."""

    def test_admin_can_suspend_tenant(self):
        """Global admin can suspend a tenant, blocking all access."""

    def test_notification_visible_across_tenants(self):
        """User notifications are user-scoped, not tenant-scoped."""

    def test_global_roles_not_tenant_scoped(self):
        """System roles and permissions are global, not per-tenant."""
```

### 10.16 Test Fixture Changes

After adding `tenant_id` (and `guild_id` where needed), test fixtures must be
updated to include these columns. Many existing tests create guilds, events,
signups, etc. without setting `tenant_id` — they will fail because it's
`NOT NULL`.

**Approach:** Create a test helper that auto-provisions tenant infrastructure:

```python
# tests/conftest.py — enhanced fixtures:

@pytest.fixture
def tenant_with_owner(db_session):
    """Create a user with their auto-provisioned tenant."""
    user = User(email="owner@test.com", username="owner")
    user.set_password("pass")
    db_session.add(user)
    db_session.flush()

    tenant = Tenant(name="Test Workspace", slug="test-ws", owner_id=user.id)
    db_session.add(tenant)
    db_session.flush()

    membership = TenantMembership(
        tenant_id=tenant.id, user_id=user.id, role="owner"
    )
    db_session.add(membership)
    user.active_tenant_id = tenant.id
    db_session.commit()

    return tenant, user

@pytest.fixture
def guild_in_tenant(tenant_with_owner, db_session):
    """Create a guild within the test tenant."""
    tenant, owner = tenant_with_owner
    guild = Guild(
        name="Test Guild",
        realm_name="Icecrown",
        tenant_id=tenant.id,
        created_by=owner.id,
    )
    db_session.add(guild)
    db_session.commit()
    return guild
```

**Estimated fixture updates:**

| Test file | Affected | Estimated changes |
|-----------|----------|-------------------|
| `tests/conftest.py` | All fixtures that create guilds/events | ~10-15 places |
| `tests/test_signups.py` | Signup creation | ~15-25 places |
| `tests/test_lineup.py` | LineupSlot creation | ~20-30 places |
| `tests/test_attendance.py` | AttendanceRecord creation | ~5-10 places |
| `tests/test_events.py` | Event + signup chains | ~10-15 places |
| `tests/test_replacements.py` | CharacterReplacement creation | ~5-10 places |
| `tests/test_permissions.py` | Various full-stack tests | ~5-10 places |
| Other test files | Various | ~10-20 places |

**Total estimated:** 80-135 test fixture updates across ~20 test files.

### 10.17 Rollout Checklist

Execute these steps **in order**. Each step must be verified before proceeding.

- [ ] **Step 0.1:** Create `app/models/tenant.py` with `Tenant`, `TenantMembership`, `TenantInvitation`
- [ ] **Step 0.2:** Create `app/models/mixins.py` with `TenantMixin`
- [ ] **Step 0.3:** Update `User` model — add `active_tenant_id`
- [ ] **Step 0.4:** Update `Guild` model — add `TenantMixin` → adds `tenant_id`
- [ ] **Step 0.5:** Update `auth_service.py` — auto-create tenant on registration
- [ ] **Step 0.6:** Run tests (expect failures due to missing `tenant_id` in fixtures)
- [ ] **Step 0.7:** Update test fixtures — add `tenant_id` to all guild/event/signup creation
- [ ] **Step 0.8:** Run full test suite — all guild-related tests pass ✅
- [ ] **Step 0.9:** Add `TenantMixin` to all guild-child models (characters, raid_definitions, etc.)
- [ ] **Step 0.10:** Add `tenant_id` + `guild_id` to Signup, LineupSlot, RaidBan, AttendanceRecord, CharacterReplacement
- [ ] **Step 0.11:** Update test fixtures for child models
- [ ] **Step 0.12:** Run full test suite ✅
- [ ] **Step 0.13:** Update all service-layer queries — add `tenant_id` filters
- [ ] **Step 0.14:** Update all API routes — pass `tenant_id` through call chain
- [ ] **Step 0.15:** Run full test suite ✅
- [ ] **Step 0.16:** Create tenant API blueprint (`app/api/v1/tenants.py`)
- [ ] **Step 0.17:** Create tenant invitation endpoints
- [ ] **Step 0.18:** Add tenant switching endpoint (`PUT /auth/active-tenant`)
- [ ] **Step 0.19:** Build frontend tenant switcher sidebar component
- [ ] **Step 0.20:** Update auth store with `activeTenantId` and `tenants[]`
- [ ] **Step 0.21:** Add `TenantsTab` to GlobalAdminView
- [ ] **Step 0.22:** Write the Alembic migration script
- [ ] **Step 0.23:** Run post-migration verification queries
- [ ] **Step 0.24:** Write `tests/test_tenant_isolation.py` — 16+ cross-tenant isolation tests
- [ ] **Step 0.25:** Run full test suite — all 632+ tests pass ✅
- [ ] **Step 0.26:** Manual smoke test:
  - Register User A → auto-tenant created
  - Register User B → auto-tenant created
  - User A creates 2 guilds, creates events, signups
  - User A generates invite link → User B accepts → User B joins Tenant A
  - User B switches between Tenant A (member) and Tenant B (owner) via sidebar
  - Verify data isolation: User B in Tenant B cannot see Tenant A's guilds
  - Global admin views all tenants, suspends one, verifies access blocked
- [ ] **Step 0.27:** Code review — audit every query for missing `tenant_id` filters

---

### 10.18 Summary of All Changes

| Area | Files | Estimated changes |
|------|-------|-------------------|
| **New files** | `app/models/tenant.py`, `app/models/mixins.py`, `app/api/v1/tenants.py`, `src/components/admin/TenantsTab.vue`, `src/components/sidebar/TenantSwitcher.vue` | 5 new files |
| **Model changes** | `user.py` (+1 field), `guild.py` (+tenant_id), `signup.py` (Signup, LineupSlot, RaidBan, CharacterReplacement +tenant_id +guild_id), `attendance.py` (+tenant_id +guild_id), all other guild-child models | ~30 lines per model |
| **Service changes** | `guild_service.py`, `event_service.py`, `signup_service.py`, `lineup_service.py`, `attendance_service.py`, `character_service.py`, `raid_service.py`, `auth_service.py` | ~80-100 query updates |
| **API changes** | `tenants.py` (new), `admin.py`, `guilds.py`, `signups.py`, `lineup.py`, `attendance.py` | ~30-40 route updates |
| **Utility changes** | `permissions.py`, `api_helpers.py`, `decorators.py`, `notify.py` | ~15-20 updates |
| **Frontend changes** | `auth.js` store, sidebar, `GlobalAdminView.vue`, `TenantsTab.vue`, `TenantSwitcher.vue` | ~200-300 lines new |
| **Test fixtures** | 10-20 test files | ~80-135 fixture updates |
| **New tests** | `tests/test_tenant_isolation.py` | 1 new file (~16 tests) |
| **Migration** | Alembic migration file | 1 file (~150 lines) |
| **Total** | ~30-40 files | ~400-600 lines changed/added |

### 10.19 What This Does NOT Cover

The following are explicitly **out of scope** for Phase 0 and will be addressed
in later phases:

| Item | Phase | Reason |
|------|-------|--------|
| Guild-level invitation system (within tenant) | Phase 2 | Separate feature — Phase 0 handles tenant-level invitations |
| Per-guild role customization | Phase 3 | Requires expansion system first |
| Multi-expansion support | Phase 4 | Build on top of tenant-isolated foundation |
| Plugin architecture | Phase 5 | Build on top of tenant-isolated foundation |
| Billing/subscription per tenant | Phase 6 | Requires tenant isolation (done in Phase 0) |
| Row-level security (Postgres RLS) | Future | Advanced DB-level enforcement; Phase 0 uses application-level |
| Separate databases per tenant | Never | Over-engineering for this application's scale; row-level tenancy with per-user tenants is sufficient |

### 10.20 Decision Record

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Per-user tenants** (not per-guild) | User registers → gets a workspace. Guilds are organizational units within the workspace. Matches true SaaS model (Slack, Discord, Notion). |
| 2 | **Row-level tenancy** (shared DB, `tenant_id` on every table) | Simple, allows cross-tenant features (user in multiple tenants), SQLite-compatible. Full DB isolation is over-engineering. |
| 3 | **Auto-create tenant on registration** | Every user immediately has a workspace. No separate "create workspace" step. Reduces friction. |
| 4 | **Invite via link / Discord / in-app** | Link is easiest for WoW community (paste in-game, forums). Discord matches existing guild communication. In-app for existing users. |
| 5 | **Tenant switching in sidebar** | Users in multiple tenants need instant context switching. Sidebar dropdown is the standard SaaS pattern (Slack, Discord). |
| 6 | **Global admin manages tenants** | Platform operator needs oversight: suspend abusive tenants, override limits, view platform stats. Separate from tenant-level admin. |
| 7 | **`TenantMixin`** (not decorator) | Explicit is better than implicit. Mixin makes `tenant_id` visible in model definition. |
| 8 | **Phase 0 before all other phases** | Retrofitting tenancy after Phases 1-5 would require re-auditing every new query. Pay the cost once, upfront. |
| 9 | **Keep `armory_configs` without `tenant_id`** | User-scoped, not tenant-scoped. Guild links via `Guild.armory_config_id` FK. |
| 10 | **Keep notifications `tenant_id` nullable** | Some notifications are system-wide (password change, etc.). User-scoped queries are correct. |
| 11 | **`active_tenant_id` on User model** | Simplest approach — server always knows which tenant context the user is in. Alternative (JWT claim) adds complexity. |
| 12 | **Configurable guild limit per tenant (`max_guilds`)** | Different plans can have different limits. Global admin can override per-tenant. Default: 3 for free plan. |

---

## 11. Frontend Multi-Tenant Migration — Complete Plan

> **Why a separate section?** Section 10 covers backend models, services, APIs,
> and migration. But the frontend is a full Vue 3 SPA with its own store layer,
> routing, composables, API modules, and 15+ views — all of which need tenant
> awareness. This section provides the **complete file-by-file frontend plan**.

---

### 11.1 Current Frontend Architecture

The frontend is a Vue 3 SPA using Vite, Pinia (state), Vue Router, Vue I18n,
Axios (HTTP), and Socket.IO (real-time). Here is the complete file inventory:

#### 11.1.1 File Inventory

| Category | Files | Lines | Tenant Impact |
|----------|-------|-------|---------------|
| **Entry** | `main.js`, `App.vue`, `i18n.js`, `constants.js` | ~210 | `main.js` bootstrap; `constants.js` stays as-is |
| **Stores (5)** | `auth.js`, `guild.js`, `calendar.js`, `constants.js`, `ui.js` | ~200 | Auth + Guild stores need major changes; new `tenant.js` store needed |
| **API modules (17)** | `index.js`, `auth.js`, `guilds.js`, `events.js`, `signups.js`, `lineup.js`, `attendance.js`, `characters.js`, `raidDefinitions.js`, `roles.js`, `templates.js`, `series.js`, `notifications.js`, `admin.js`, `meta.js`, `warmane.js`, `armory.js` | ~450 | Axios interceptor needs `X-Tenant-Id`; new `tenants.js` API module |
| **Views (15)** | `LoginView`, `RegisterView`, `DashboardView`, `CalendarView`, `RaidDetailView`, `CharacterManagerView`, `AttendanceView`, `UserProfileView`, `AdminPanelView`, `GlobalAdminView`, `GuildSettingsView`, `RaidDefinitionsView`, `TemplatesView`, `SeriesView`, `RolesManagementView` | ~5,500 | Most views unaffected (tenant context via stores); Register, GlobalAdmin need changes |
| **Layout (4)** | `AppShell.vue`, `AppSidebar.vue`, `AppTopBar.vue`, `AppBottomNav.vue` | ~950 | AppSidebar needs tenant switcher; AppTopBar shows tenant name |
| **Admin components (9)** | `DashboardTab`, `UsersTab`, `RolesTab`, `GuildsTab`, `DefaultRaidDefinitionsTab`, `SettingsTab`, `GuildSettingsTab`, `MembersTab`, `SystemTab` | ~3,500 | New `TenantsTab`; DashboardTab adds tenant stats |
| **Common components (13)** | `WowCard`, `WowButton`, `WowModal`, `WowTooltip`, `ClassBadge`, `RoleBadge`, `SpecBadge`, `StatusBadge`, `LockBadge`, `RaidSizeBadge`, `RealmBadge`, `CharacterDetailModal`, `CharacterTooltip` | ~700 | None — these are presentation-only |
| **Composables (9)** | `useAuth`, `usePermissions`, `useSocket`, `useFormatting`, `useTimezone`, `useDragDrop`, `useSystemSettings`, `useWowIcons`, `useWowheadTooltips` | ~830 | `usePermissions` needs tenant context; `useSocket` needs tenant rooms |
| **Router** | `router/index.js` | ~150 | New invite route; tenant context in guards |
| **Total** | ~72 files | ~12,500 | ~25-30 files need changes |

#### 11.1.2 Current Data Flow

```
User logs in → auth store (user object)
            → guild store (user's guilds) → currentGuild selected
            → calendar store (events for currentGuild)
            → constants store (WoW classes, specs, roles, realms)

Every view reads from stores; API calls go through /api/v1/*
Guild context = guildStore.currentGuild.id (used in API calls)

No tenant concept exists anywhere in the frontend today.
```

#### 11.1.3 Target Data Flow (After Tenancy)

```
User logs in → auth store (user + activeTenantId + tenants[])
            → tenant store (active tenant details, members, invitations)
            → guild store (guilds within active tenant)
            → calendar store (events for currentGuild within active tenant)
            → constants store (no change — global)

Tenant switch → tenant store updates activeTenantId
             → guild store reloads (different guilds)
             → calendar store reloads (different events)
             → permissions reload (different roles/permissions per tenant)
             → Socket.IO leaves old tenant rooms, joins new ones
```

---

### 11.2 Store Layer Changes

#### 11.2.1 New Store: `src/stores/tenant.js`

```javascript
// src/stores/tenant.js (NEW FILE)

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as tenantsApi from '@/api/tenants'

export const useTenantStore = defineStore('tenant', () => {
  // ── State ──
  const tenants = ref([])              // All tenants user belongs to (owned + member)
  const activeTenantId = ref(null)     // Currently active tenant ID
  const activeTenant = ref(null)       // Full details of active tenant
  const members = ref([])              // Members of active tenant
  const invitations = ref([])          // Pending invitations for active tenant
  const loading = ref(false)
  const error = ref(null)

  // ── Derived ──
  const ownedTenants = computed(() =>
    tenants.value.filter(t => t.role === 'owner')
  )
  const memberTenants = computed(() =>
    tenants.value.filter(t => t.role !== 'owner')
  )
  const isOwner = computed(() =>
    activeTenant.value?.role === 'owner'
  )
  const isAdmin = computed(() =>
    ['owner', 'admin'].includes(activeTenant.value?.role)
  )
  const canCreateGuild = computed(() =>
    isOwner.value || isAdmin.value
  )
  const guildCount = computed(() =>
    activeTenant.value?.guild_count ?? 0
  )
  const maxGuilds = computed(() =>
    activeTenant.value?.max_guilds ?? 3
  )
  const atGuildLimit = computed(() =>
    guildCount.value >= maxGuilds.value
  )

  // ── Actions ──
  async function fetchTenants() {
    loading.value = true
    error.value = null
    try {
      tenants.value = await tenantsApi.getTenants()
      if (!activeTenantId.value && tenants.value.length > 0) {
        // Default to the user's owned tenant (first in list)
        activeTenantId.value = tenants.value[0].id
      }
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load tenants'
    } finally {
      loading.value = false
    }
  }

  async function fetchActiveTenant() {
    if (!activeTenantId.value) return
    try {
      activeTenant.value = await tenantsApi.getTenant(activeTenantId.value)
    } catch { /* ignore */ }
  }

  async function switchTenant(tenantId) {
    loading.value = true
    try {
      await tenantsApi.setActiveTenant(tenantId)
      activeTenantId.value = tenantId
      await fetchActiveTenant()
      // Stores that depend on tenant context will reload via watchers
    } finally {
      loading.value = false
    }
  }

  async function fetchMembers() {
    if (!activeTenantId.value) return
    try {
      members.value = await tenantsApi.getTenantMembers(activeTenantId.value)
    } catch { /* ignore */ }
  }

  async function fetchInvitations() {
    if (!activeTenantId.value) return
    try {
      invitations.value = await tenantsApi.getTenantInvitations(activeTenantId.value)
    } catch { /* ignore */ }
  }

  function reset() {
    tenants.value = []
    activeTenantId.value = null
    activeTenant.value = null
    members.value = []
    invitations.value = []
  }

  return {
    // state
    tenants, activeTenantId, activeTenant, members, invitations,
    loading, error,
    // derived
    ownedTenants, memberTenants, isOwner, isAdmin,
    canCreateGuild, guildCount, maxGuilds, atGuildLimit,
    // actions
    fetchTenants, fetchActiveTenant, switchTenant,
    fetchMembers, fetchInvitations, reset,
  }
})
```

#### 11.2.2 Changes to `src/stores/auth.js`

```javascript
// Current auth store has: user, loading, error, fetchMe, login, register, logout

// Changes needed:
// 1. fetchMe() response now includes active_tenant_id and tenants[]
// 2. After login/register, auto-set tenant context
// 3. logout() must reset tenant store

// Modified fetchMe:
async function fetchMe() {
  // ...existing code...
  const data = await authApi.getMe()
  user.value = data
  // NEW: Initialize tenant store from user data
  const tenantStore = useTenantStore()
  if (data.active_tenant_id) {
    tenantStore.activeTenantId = data.active_tenant_id
  }
  await tenantStore.fetchTenants()
}

// Modified register:
async function register(username, email, password) {
  // ...existing code...
  const data = await authApi.register({ username, email, password })
  user.value = data.user ?? data
  // NEW: Backend auto-creates tenant — set it as active
  const tenantStore = useTenantStore()
  if (data.tenant_id || data.user?.active_tenant_id) {
    tenantStore.activeTenantId = data.tenant_id || data.user.active_tenant_id
    await tenantStore.fetchTenants()
  }
}

// Modified logout:
async function logout() {
  // ...existing code...
  user.value = null
  // NEW: Clear tenant state
  const tenantStore = useTenantStore()
  tenantStore.reset()
}
```

#### 11.2.3 Changes to `src/stores/guild.js`

The guild store currently lists all guilds the user is a member of. After
tenancy, it must only show guilds **within the active tenant**.

```javascript
// Key change: fetchGuilds() is already called from router guard.
// After tenancy, the backend API already filters by active_tenant_id.
// So the guild store itself doesn't need to know about tenants — the
// backend handles the scoping. However, we need to:

// 1. Add a watcher to re-fetch when tenant changes
// 2. Reset currentGuild on tenant switch

import { useTenantStore } from '@/stores/tenant'

// Inside the store setup:
const tenantStore = useTenantStore()

// Watch for tenant switch → reload guilds
watch(() => tenantStore.activeTenantId, (newId, oldId) => {
  if (oldId && newId !== oldId) {
    currentGuild.value = null
    members.value = []
    fetchGuilds()  // Reload guilds for new tenant
  }
})
```

#### 11.2.4 Changes to `src/stores/calendar.js`

The calendar store fetches events via `getAllEvents()`. After tenancy, the
backend API filters by active tenant. The calendar store needs to:

```javascript
// Reset events on tenant switch:
import { useTenantStore } from '@/stores/tenant'

const tenantStore = useTenantStore()

watch(() => tenantStore.activeTenantId, (newId, oldId) => {
  if (oldId && newId !== oldId) {
    events.value = []
    // Calendar will re-fetch via the CalendarView's onMounted
  }
})
```

#### 11.2.5 `src/stores/constants.js` — No Changes

The constants store serves global WoW data (classes, specs, roles, realms). This
data is **not tenant-scoped** — it's the same for all tenants. ✅ No changes.

#### 11.2.6 `src/stores/ui.js` — No Changes

The UI store manages sidebar state, modals, and toasts. These are purely
local UI state. ✅ No changes.

---

### 11.3 API Layer Changes

#### 11.3.1 New API Module: `src/api/tenants.js`

```javascript
// src/api/tenants.js (NEW FILE)

import api from '.'

// ── Tenant CRUD ──
export const getTenants = () => api.get('/tenants')
export const getTenant = (id) => api.get(`/tenants/${id}`)
export const updateTenant = (id, data) => api.put(`/tenants/${id}`, data)
export const deleteTenant = (id) => api.delete(`/tenants/${id}`)

// ── Tenant Members ──
export const getTenantMembers = (id) => api.get(`/tenants/${id}/members`)
export const addTenantMember = (id, data) => api.post(`/tenants/${id}/members`, data)
export const updateTenantMember = (id, userId, data) => api.put(`/tenants/${id}/members/${userId}`, data)
export const removeTenantMember = (id, userId) => api.delete(`/tenants/${id}/members/${userId}`)

// ── Tenant Invitations ──
export const getTenantInvitations = (id) => api.get(`/tenants/${id}/invitations`)
export const createTenantInvitation = (id, data) => api.post(`/tenants/${id}/invitations`, data)
export const revokeInvitation = (tenantId, invId) => api.delete(`/tenants/${tenantId}/invitations/${invId}`)
export const acceptInvite = (token) => api.post(`/invite/${token}`)

// ── Tenant Switching ──
export const setActiveTenant = (tenantId) => api.put('/auth/active-tenant', { tenant_id: tenantId })
export const getActiveTenant = () => api.get('/auth/active-tenant')
```

#### 11.3.2 Axios Interceptor — Tenant Context Header

The Axios instance (`src/api/index.js`) needs a request interceptor that
attaches the active tenant ID to every request. This allows the backend to
know which tenant context to use without changing every API call signature.

```javascript
// src/api/index.js — ADD request interceptor:

import { useTenantStore } from '@/stores/tenant'

// Request interceptor — attach tenant context
api.interceptors.request.use(config => {
  // Lazy import to avoid circular dependency at module-evaluation time
  try {
    const tenantStore = useTenantStore()
    if (tenantStore.activeTenantId) {
      config.headers['X-Tenant-Id'] = tenantStore.activeTenantId
    }
  } catch {
    // Store not yet initialized (e.g., during app bootstrap) — skip
  }
  return config
})
```

> **Note:** The backend already knows the active tenant from `user.active_tenant_id`
> (session/cookie). The `X-Tenant-Id` header is an **additional safety check** —
> if the header doesn't match the user's active tenant, the backend rejects the
> request. This prevents stale tenant context from a browser tab that missed a
> tenant switch.

#### 11.3.3 Changes to `src/api/admin.js`

```javascript
// ADD new admin tenant endpoints:
export const getAdminTenants = () => api.get('/admin/tenants')
export const getAdminTenant = (id) => api.get(`/admin/tenants/${id}`)
export const updateAdminTenant = (id, data) => api.put(`/admin/tenants/${id}`, data)
export const suspendTenant = (id) => api.post(`/admin/tenants/${id}/suspend`)
export const activateTenant = (id) => api.post(`/admin/tenants/${id}/activate`)
export const deleteAdminTenant = (id) => api.delete(`/admin/tenants/${id}`)
export const updateTenantLimits = (id, data) => api.put(`/admin/tenants/${id}/limits`, data)
```

#### 11.3.4 Other API Modules — No Changes Needed

All other API modules (`guilds.js`, `events.js`, `signups.js`, `lineup.js`,
`attendance.js`, `characters.js`, `raidDefinitions.js`, `roles.js`,
`templates.js`, `series.js`, `notifications.js`, `meta.js`, `warmane.js`,
`armory.js`) **do not need changes**. The tenant context is attached
automatically via the Axios interceptor (`X-Tenant-Id` header) and the
backend resolves the tenant from the user's session. The existing guild-scoped
API calls (`/guilds/<id>/...`) continue to work — the backend just adds a
tenant ownership check. ✅

---

### 11.4 Router Changes

#### 11.4.1 New Routes

```javascript
// Add to routes array in src/router/index.js:

{
  path: '/invite/:token',
  name: 'invite-accept',
  component: () => import('@/views/InviteAcceptView.vue'),
  meta: { requiresAuth: false }  // Can be accessed before login
},
{
  path: '/tenant/settings',
  name: 'tenant-settings',
  component: () => import('@/views/TenantSettingsView.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/tenant/invite',
  name: 'tenant-invite',
  component: () => import('@/views/TenantInviteView.vue'),
  meta: { requiresAuth: true }
},
```

#### 11.4.2 Router Guard — Tenant Bootstrap

The current router guard flow is:
1. `fetchMe()` → restore session
2. `fetchGuilds()` → load user's guilds

After tenancy, the flow becomes:
1. `fetchMe()` → restore session + `active_tenant_id`
2. `fetchTenants()` → load user's tenants
3. `fetchGuilds()` → load guilds within active tenant

```javascript
// Modified router guard (src/router/index.js):

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (!_authChecked) {
    _authChecked = true
    try {
      const constantsStore = useConstantsStore()
      const authPromise = authStore.fetchMe()
      constantsStore.fetchConstants()
      await authPromise

      if (authStore.user) {
        // NEW: Bootstrap tenant context
        const tenantStore = useTenantStore()
        await tenantStore.fetchTenants()

        // Then load guilds (now tenant-scoped)
        const guildStore = useGuildStore()
        await guildStore.fetchGuilds()
      }
    } catch {
      // Not authenticated
    }
  }

  // ... rest of guard unchanged ...
})
```

#### 11.4.3 Invite Link Handling

When a user clicks an invite link (`/invite/{token}`), the router should:
1. If logged in → show "Join {tenant_name}?" confirmation page
2. If not logged in → redirect to `/login?redirect=/invite/{token}` →
   after login, auto-redirect back to invite page

This is handled automatically by the existing `requiresAuth: false` meta
and the redirect logic in the router guard.

---

### 11.5 Layout & Shell Changes

#### 11.5.1 `AppSidebar.vue` — Tenant Switcher

The sidebar currently has:
1. Logo/branding
2. Guild switcher dropdown
3. Available guilds to join
4. Create guild button
5. Navigation links
6. User info

**After tenancy**, it needs a **tenant switcher** above the guild switcher:

```
┌─────────────────────────────────────────┐
│  Logo / Branding                         │
├─────────────────────────────────────────┤
│  🏠 Workspace                    (NEW)   │
│  ┌─────────────────────────────────────┐│
│  │ ▼ My Workspace                  ✓  │ │
│  │   Thrall's Guild Hub               │ │
│  │   PvP League (invited)             │ │
│  └─────────────────────────────────────┘│
├─────────────────────────────────────────┤
│  ⚔️ Guild                               │
│  ┌─────────────────────────────────────┐│
│  │ ▼ Select Guild...                  │ │
│  └─────────────────────────────────────┘│
│  [+ Create Guild] (if under limit)      │
├─────────────────────────────────────────┤
│  📅 Calendar                            │
│  ⚔️ Dashboard                           │
│  👤 Characters                          │
│  📊 Attendance                          │
│  ...                                    │
├─────────────────────────────────────────┤
│  ⚙️ Tenant Settings (owner/admin)       │
│  👥 Invite Players (owner/admin)        │
│  🛡️ Guild Admin                         │
│  🔧 Global Admin (if global admin)      │
├─────────────────────────────────────────┤
│  User info                              │
└─────────────────────────────────────────┘
```

**Implementation approach:**

The tenant switcher is extracted into a new component `TenantSwitcher.vue`
and imported into `AppSidebar.vue`. This keeps the sidebar manageable.

```vue
<!-- New section in AppSidebar.vue, above the guild switcher: -->
<div class="px-4 py-3 border-b border-[#2a3450]">
  <TenantSwitcher />
</div>
```

**Changes to AppSidebar.vue:**

| # | Change | Details |
|---|--------|---------|
| 1 | Import `TenantSwitcher` component | New child component |
| 2 | Add tenant switcher section above guild switcher | New `<div>` block |
| 3 | "Create Guild" respects tenant guild limit | `canCreateGuild` checks `tenantStore.atGuildLimit` |
| 4 | Remove "available guilds to join" section | Guild joining happens within tenant context now |
| 5 | Add "Tenant Settings" nav link (owner/admin only) | Below main nav |
| 6 | Add "Invite Players" nav link (owner/admin only) | Below main nav |

#### 11.5.2 `AppTopBar.vue` — Tenant Name Display

Currently shows `guildStore.currentGuild?.name` in the top bar. After tenancy,
also show the tenant name as context:

```vue
<!-- Modified top bar header: -->
<div>
  <h1 class="text-sm font-bold text-accent-gold font-wow leading-tight">
    {{ guildStore.currentGuild?.name ?? t('topBar.noGuild') }}
  </h1>
  <!-- NEW: Show active tenant name as subtitle -->
  <p class="text-xs text-text-muted leading-tight">
    {{ tenantStore.activeTenant?.name ?? '' }}
  </p>
</div>
```

**Changes to AppTopBar.vue:**

| # | Change | Details |
|---|--------|---------|
| 1 | Import `useTenantStore` | Access active tenant |
| 2 | Show tenant name below guild name | Subtitle/context line |
| 3 | No other changes | Notifications, profile dropdown stay the same |

#### 11.5.3 `AppBottomNav.vue` — No Changes

The mobile bottom navigation shows Dashboard, Calendar, Characters, Attendance,
Guild. This is fine for tenancy — the tenant context is implicit via the
sidebar. ✅ No changes needed.

#### 11.5.4 `AppShell.vue` — No Changes

The shell is a flex container for sidebar + main content + toast. No tenant
awareness needed at this level. ✅ No changes.

---

### 11.6 View-by-View Migration Audit

Every view is assessed for tenant impact. Most views **require zero changes**
because they operate through stores and API calls that already have tenant
context via the interceptor/backend.

#### 11.6.1 Views That Need Changes

| View | File | Change | Reason |
|------|------|--------|--------|
| **RegisterView** | `RegisterView.vue` | Minor | After registration, auto-redirect to dashboard (tenant is auto-created). Show success message mentioning workspace. |
| **GlobalAdminView** | `GlobalAdminView.vue` | Medium | Add new `TenantsTab` tab to the 6 existing tabs (becomes 7). Import `TenantsTab` component. |
| **DashboardView** | `DashboardView.vue` | Minor | Show tenant name in welcome message: "Welcome to {tenant_name}, {username}". Optionally show tenant stats (guild count, member count). |
| **GuildSettingsView** | `GuildSettingsView.vue` | None → Minor | Guild creation flow may need to check tenant guild limit. Currently in sidebar, but if guild settings view allows creating, check limit. |

#### 11.6.2 Views That Need Zero Changes

| View | File | Why No Change |
|------|------|---------------|
| **LoginView** | `LoginView.vue` | Login flow is tenant-agnostic; tenant context set after login |
| **CalendarView** | `CalendarView.vue` | Reads from calendar store (already tenant-scoped via backend) |
| **RaidDetailView** | `RaidDetailView.vue` | Fetches single event by ID; backend verifies tenant ownership |
| **CharacterManagerView** | `CharacterManagerView.vue` | Characters are guild-scoped; backend filters by tenant |
| **AttendanceView** | `AttendanceView.vue` | Guild-scoped; backend filters by tenant |
| **UserProfileView** | `UserProfileView.vue` | User-scoped (global); not tenant-specific |
| **AdminPanelView** | `AdminPanelView.vue` | Guild admin panel; works within current guild (tenant-scoped by backend) |
| **RaidDefinitionsView** | `RaidDefinitionsView.vue` | Guild-scoped; backend filters by tenant |
| **TemplatesView** | `TemplatesView.vue` | Guild-scoped; backend filters by tenant |
| **SeriesView** | `SeriesView.vue` | Guild-scoped; backend filters by tenant |
| **RolesManagementView** | `RolesManagementView.vue` | Guild-scoped; backend filters by tenant |

#### 11.6.3 New Views

| View | File | Purpose |
|------|------|---------|
| **InviteAcceptView** | `InviteAcceptView.vue` | Public page: shows tenant name + accept/decline invitation |
| **TenantSettingsView** | `TenantSettingsView.vue` | Tenant owner: edit name, view plan/limits, manage members |
| **TenantInviteView** | `TenantInviteView.vue` | Tenant owner/admin: create invite links, view pending invitations |

---

### 11.7 Component Migration Audit

#### 11.7.1 Admin Tab Components — Changes Needed

| Component | File | Change |
|-----------|------|--------|
| **TenantsTab** (NEW) | `src/components/admin/TenantsTab.vue` | New component: list all tenants, view details, edit limits, suspend/activate, delete. ~200-300 lines. |
| **DashboardTab** | `DashboardTab.vue` | Add tenant-related stats to dashboard: total tenants, active tenants, suspended tenants |
| **GuildsTab** | `GuildsTab.vue` | Add "Tenant" column to guild list showing which tenant each guild belongs to |
| **UsersTab** | `UsersTab.vue` | Add "Tenants" column showing how many tenants each user belongs to |

#### 11.7.2 Admin Tab Components — No Changes

| Component | Why No Change |
|-----------|---------------|
| **RolesTab** | System roles are global, not tenant-scoped |
| **DefaultRaidDefinitionsTab** | Default raid defs are global (guild_id=NULL) |
| **SettingsTab** | System settings are global |
| **GuildSettingsTab** | Guild settings work within tenant context (backend-scoped) |
| **MembersTab** | Guild member management works within tenant context |
| **SystemTab** | Legacy component; no active use |

#### 11.7.3 New Components

| Component | File | Purpose | Est. Lines |
|-----------|------|---------|-----------|
| **TenantSwitcher** | `src/components/layout/TenantSwitcher.vue` | Dropdown for switching between tenants in sidebar | ~80-120 |
| **TenantsTab** | `src/components/admin/TenantsTab.vue` | Global admin: tenant management table with actions | ~250-350 |
| **TenantMembersModal** | `src/components/admin/TenantMembersModal.vue` | Global admin: view/manage members of a specific tenant | ~150-200 |
| **InviteLinkCard** | `src/components/common/InviteLinkCard.vue` | Display invite link with copy button, expiry info | ~60-80 |

#### 11.7.4 Common Components — No Changes

All 13 common components (`WowCard`, `WowButton`, `WowModal`, `ClassBadge`,
`RoleBadge`, `SpecBadge`, `StatusBadge`, `LockBadge`, `RaidSizeBadge`,
`RealmBadge`, `WowTooltip`, `CharacterDetailModal`, `CharacterTooltip`) are
purely presentational. They render data passed via props. They have no concept
of guilds, tenants, or API calls. ✅ No changes needed.

---

### 11.8 Composable Changes

#### 11.8.1 `usePermissions.js` — Tenant-Aware

Currently, `usePermissions()` fetches permissions for the **current guild**.
After tenancy, it needs to also consider **tenant-level roles** (owner, admin,
member). The tenant role determines what the user can do at the workspace level
(create guilds, invite players, manage tenant settings).

```javascript
// Add tenant-level permission helpers:

const tenantStore = useTenantStore()

const tenantRole = computed(() => tenantStore.activeTenant?.role ?? null)
const isTenantOwner = computed(() => tenantRole.value === 'owner')
const isTenantAdmin = computed(() => ['owner', 'admin'].includes(tenantRole.value))

// Tenant-level permissions:
function canTenant(action) {
  if (currentUser.value?.is_admin === true) return true
  switch (action) {
    case 'create_guild': return isTenantAdmin.value && !tenantStore.atGuildLimit
    case 'invite_member': return isTenantAdmin.value
    case 'manage_settings': return isTenantOwner.value
    case 'manage_members': return isTenantAdmin.value
    default: return false
  }
}

// Return in addition to existing:
return { ..., tenantRole, isTenantOwner, isTenantAdmin, canTenant }
```

#### 11.8.2 `useSocket.js` — Tenant Rooms

Currently, Socket.IO joins guild rooms (`join_guild`) and event rooms
(`join_event`). After tenancy, it should also join a **tenant room** for
tenant-level real-time updates (e.g., new member joined, invitation accepted).

```javascript
// Add to useSocket.js:

/** Join the Socket.IO room for the active tenant. */
function joinTenant(tenantId) {
  s.emit('join_tenant', { tenant_id: Number(tenantId) })
}

/** Leave the Socket.IO room for a tenant. */
function leaveTenant(tenantId) {
  s.emit('leave_tenant', { tenant_id: Number(tenantId) })
}

// Return in addition to existing:
return { ..., joinTenant, leaveTenant }
```

#### 11.8.3 Other Composables — No Changes

| Composable | Why No Change |
|------------|---------------|
| `useAuth.js` | Wraps auth store; store handles tenant context |
| `useFormatting.js` | Pure formatting utilities |
| `useTimezone.js` | Timezone conversion; no tenant dependency |
| `useDragDrop.js` | Drag/drop handler; UI-only |
| `useSystemSettings.js` | Global system settings; not tenant-scoped |
| `useWowIcons.js` | Static WoW icon mapping; not tenant-scoped |
| `useWowheadTooltips.js` | External tooltip integration; no tenant dependency |

---

### 11.9 New Component Specifications

#### 11.9.1 `TenantSwitcher.vue`

```vue
<!-- src/components/layout/TenantSwitcher.vue -->
<!--
  Dropdown component in the sidebar that shows all tenants the user
  belongs to. Clicking a different tenant triggers a full context switch.
  
  Behavior:
  - Shows tenant name + role badge (Owner/Admin/Member)
  - Active tenant has a checkmark
  - Switching triggers: store update → API call → full data reload
  - Shows tenant plan badge if applicable
-->
<template>
  <div>
    <label class="text-xs text-text-muted uppercase tracking-wider mb-1 block">
      {{ t('tenant.workspace') }}
    </label>
    <select
      :value="tenantStore.activeTenantId"
      class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none"
      @change="onSwitch"
    >
      <option
        v-for="t in tenantStore.tenants"
        :key="t.id"
        :value="t.id"
      >{{ t.name }} ({{ t.role }})</option>
    </select>
  </div>
</template>
```

#### 11.9.2 `TenantsTab.vue` (Global Admin)

```
Features:
- Table listing all tenants with columns:
  ID | Name | Owner | Plan | Guilds (used/max) | Members (used/max) | Status | Actions
- Actions per tenant:
  - View Details → modal with tenant info + member list
  - Edit Limits → modal to change max_guilds, max_members, plan
  - Suspend → confirmation dialog → POST /admin/tenants/{id}/suspend
  - Activate → POST /admin/tenants/{id}/activate
  - Delete → confirmation dialog → DELETE /admin/tenants/{id}
- Search/filter by name, owner, plan, status
- Pagination for large tenant lists

Estimated: ~250-350 lines (similar complexity to existing GuildsTab)
```

#### 11.9.3 `InviteAcceptView.vue`

```
Features:
- Public page (no auth required for viewing)
- Fetches invite details by token: GET /api/v1/invite/{token}/details
- Shows: tenant name, inviter name, role being assigned, expiry
- If user is logged in: "Accept" / "Decline" buttons
- If user is NOT logged in: "Login to Accept" / "Register to Accept" buttons
  (redirect back after auth)
- After accepting: redirect to dashboard with tenant switched to the new one

Estimated: ~120-180 lines
```

#### 11.9.4 `TenantSettingsView.vue`

```
Features:
- Only accessible to tenant owner/admin
- Sections:
  1. Tenant Details: name (editable), slug (display), plan (display)
  2. Limits: guilds used/max, members used/max (display)
  3. Members: table of all tenant members with role, status, actions
     - Change role (admin/member)
     - Remove member (with confirmation)
  4. Invitations: list pending invites, revoke links
  5. Danger Zone: delete tenant (owner only, with confirmation)

Estimated: ~300-400 lines
```

#### 11.9.5 `TenantInviteView.vue`

```
Features:
- Only accessible to tenant owner/admin
- Create new invite:
  - Type: link / direct (search for user)
  - Role: member / admin
  - Max uses: unlimited / 1 / 5 / 10 / custom
  - Expiry: never / 24h / 7d / 30d / custom
- Copy link button for shareable invites
- Table of existing invitations:
  - Token (truncated), type, role, uses (count/max), expiry, status, actions (revoke)
- Discord integration (future): "Send via Discord" button

Estimated: ~200-300 lines
```

---

### 11.10 I18n Additions

New translation keys needed across `translations/en.json` and
`translations/pl.json`:

```json
{
  "tenant": {
    "workspace": "Workspace",
    "myWorkspace": "My Workspace",
    "switchWorkspace": "Switch Workspace",
    "settings": "Workspace Settings",
    "invitePlayers": "Invite Players",
    "createInvite": "Create Invitation",
    "inviteLink": "Invite Link",
    "copyLink": "Copy Link",
    "linkCopied": "Link copied to clipboard!",
    "maxUses": "Max Uses",
    "unlimited": "Unlimited",
    "expiresIn": "Expires In",
    "never": "Never",
    "pending": "Pending",
    "accepted": "Accepted",
    "declined": "Declined",
    "expired": "Expired",
    "revoke": "Revoke",
    "revokeConfirm": "Are you sure you want to revoke this invitation?",
    "members": "Workspace Members",
    "owner": "Owner",
    "admin": "Admin",
    "member": "Member",
    "changeRole": "Change Role",
    "removeMember": "Remove Member",
    "removeMemberConfirm": "Remove {name} from this workspace?",
    "plan": "Plan",
    "free": "Free",
    "pro": "Pro",
    "enterprise": "Enterprise",
    "guildsUsed": "{count}/{max} guilds",
    "membersUsed": "{count}/{max} members",
    "atGuildLimit": "Guild limit reached ({max})",
    "dangerZone": "Danger Zone",
    "deleteTenant": "Delete Workspace",
    "deleteTenantConfirm": "This will permanently delete the workspace and ALL its data. This action cannot be undone.",
    "suspended": "Suspended",
    "active": "Active"
  },
  "invite": {
    "title": "You've Been Invited!",
    "joinWorkspace": "Join {name}",
    "invitedBy": "Invited by {name}",
    "assignedRole": "You'll join as: {role}",
    "expiresAt": "This invite expires {date}",
    "accept": "Accept Invitation",
    "decline": "Decline",
    "loginToAccept": "Login to Accept",
    "registerToAccept": "Register to Accept",
    "invalidToken": "This invitation link is invalid or has expired.",
    "alreadyMember": "You're already a member of this workspace.",
    "accepted": "You've joined {name}!"
  },
  "admin": {
    "tenants": {
      "tabTitle": "Tenants",
      "title": "All Tenants",
      "name": "Name",
      "owner": "Owner",
      "plan": "Plan",
      "guilds": "Guilds",
      "members": "Members",
      "status": "Status",
      "actions": "Actions",
      "viewDetails": "View Details",
      "editLimits": "Edit Limits",
      "suspend": "Suspend",
      "activate": "Activate",
      "delete": "Delete",
      "suspendConfirm": "Suspend {name}? All users will lose access.",
      "deleteConfirm": "Delete {name}? All data will be permanently lost.",
      "totalTenants": "Total Tenants",
      "activeTenants": "Active Tenants",
      "suspendedTenants": "Suspended"
    }
  }
}
```

**Estimated:** ~80-100 new translation keys per language (en.json, pl.json).

---

### 11.11 File-by-File Change Summary

#### New Files (8)

| # | File | Purpose | Est. Lines |
|---|------|---------|-----------|
| 1 | `src/stores/tenant.js` | Tenant Pinia store | ~120 |
| 2 | `src/api/tenants.js` | Tenant API module | ~25 |
| 3 | `src/components/layout/TenantSwitcher.vue` | Sidebar tenant dropdown | ~100 |
| 4 | `src/components/admin/TenantsTab.vue` | Global admin tenant management | ~300 |
| 5 | `src/views/InviteAcceptView.vue` | Accept invitation page | ~150 |
| 6 | `src/views/TenantSettingsView.vue` | Tenant owner settings page | ~350 |
| 7 | `src/views/TenantInviteView.vue` | Create/manage invitations page | ~250 |
| 8 | `src/components/common/InviteLinkCard.vue` | Reusable invite link display | ~70 |
| | **Subtotal** | | **~1,365** |

#### Modified Files (12)

| # | File | Changes | Est. Lines Changed |
|---|------|---------|-------------------|
| 1 | `src/stores/auth.js` | Add tenant bootstrap on login/register, reset on logout | ~15 |
| 2 | `src/stores/guild.js` | Watch tenant switch → reload guilds, clear current guild | ~10 |
| 3 | `src/stores/calendar.js` | Watch tenant switch → clear events | ~8 |
| 4 | `src/api/index.js` | Add `X-Tenant-Id` request interceptor | ~12 |
| 5 | `src/api/admin.js` | Add tenant admin API functions | ~10 |
| 6 | `src/router/index.js` | Add 3 routes + tenant bootstrap in guard | ~20 |
| 7 | `src/components/layout/AppSidebar.vue` | Add TenantSwitcher, tenant nav links, guild limit check | ~30 |
| 8 | `src/components/layout/AppTopBar.vue` | Show tenant name below guild name | ~5 |
| 9 | `src/views/GlobalAdminView.vue` | Add TenantsTab (7th tab) | ~10 |
| 10 | `src/views/RegisterView.vue` | Post-registration tenant welcome message | ~5 |
| 11 | `src/composables/usePermissions.js` | Add tenant-level permission helpers | ~20 |
| 12 | `src/composables/useSocket.js` | Add `joinTenant`/`leaveTenant` | ~10 |
| | **Subtotal** | | **~155** |

#### I18n Files (2)

| # | File | Changes |
|---|------|---------|
| 1 | `translations/en.json` | Add ~80-100 tenant/invite keys |
| 2 | `translations/pl.json` | Add ~80-100 tenant/invite keys (Polish) |

#### Unchanged Files (~52)

All views, components, composables, and API modules not listed above remain
unchanged. The tenant context is handled transparently by the store layer
and the Axios interceptor.

#### Grand Total

| Category | New Lines | Changed Lines |
|----------|-----------|---------------|
| New files (8) | ~1,365 | — |
| Modified files (12) | — | ~155 |
| I18n additions | ~200 | — |
| **Total** | **~1,565** | **~155** |
| **Combined** | | **~1,720 lines** |

---

### 11.12 Frontend Migration Order

Execute these steps **in order**, matching the backend Phase 0 rollout steps
(§10.17). Frontend work begins after backend steps 0.16-0.18 (tenant API,
invitations, switching endpoints are built).

- [ ] **Step F.1:** Create `src/stores/tenant.js` (tenant store)
- [ ] **Step F.2:** Create `src/api/tenants.js` (tenant API module)
- [ ] **Step F.3:** Update `src/api/index.js` — add `X-Tenant-Id` interceptor
- [ ] **Step F.4:** Update `src/stores/auth.js` — integrate tenant bootstrap
- [ ] **Step F.5:** Update `src/stores/guild.js` — watch tenant switch
- [ ] **Step F.6:** Update `src/stores/calendar.js` — watch tenant switch
- [ ] **Step F.7:** Update `src/router/index.js` — tenant guard + new routes
- [ ] **Step F.8:** Create `TenantSwitcher.vue` component
- [ ] **Step F.9:** Update `AppSidebar.vue` — add tenant switcher + nav links
- [ ] **Step F.10:** Update `AppTopBar.vue` — show tenant name
- [ ] **Step F.11:** Update `usePermissions.js` — add tenant-level permissions
- [ ] **Step F.12:** Update `useSocket.js` — add tenant rooms
- [ ] **Step F.13:** Create `InviteAcceptView.vue`
- [ ] **Step F.14:** Create `TenantSettingsView.vue`
- [ ] **Step F.15:** Create `TenantInviteView.vue`
- [ ] **Step F.16:** Create `InviteLinkCard.vue`
- [ ] **Step F.17:** Update `src/api/admin.js` — add tenant admin functions
- [ ] **Step F.18:** Create `TenantsTab.vue` (global admin)
- [ ] **Step F.19:** Update `GlobalAdminView.vue` — add TenantsTab (7th tab)
- [ ] **Step F.20:** Update `DashboardView.vue` — tenant welcome message
- [ ] **Step F.21:** Update `RegisterView.vue` — post-registration tenant message
- [ ] **Step F.22:** Add i18n keys to `translations/en.json` and `translations/pl.json`
- [ ] **Step F.23:** Run `npx vite build` — verify no build errors
- [ ] **Step F.24:** Manual smoke test:
  - Register → tenant auto-created → dashboard shows "Welcome to {workspace}"
  - Sidebar shows tenant switcher with 1 workspace
  - Create guild → respects tenant limit
  - Generate invite link → copy to clipboard
  - Second user accepts invite → appears in first user's tenant
  - Second user has two tenants → switch via sidebar → data context changes
  - Global admin → Tenants tab → sees all tenants, can suspend/activate
- [ ] **Step F.25:** Verify existing frontend behavior is unaffected:
  - Calendar loads events correctly
  - Raid detail page works
  - Signup/lineup/attendance flows work
  - Guild settings/roles/raid definitions work
  - Notifications work (cross-tenant)

---

### 11.13 Tenant Switching UX — Detailed Behavior

When a user clicks a different tenant in the sidebar dropdown, the following
sequence happens:

```
                                      Frontend                                        Backend
                                    ─────────                                       ─────────
User clicks "Thrall's Hub"
        │
        ▼
TenantSwitcher.vue
  onSwitch(tenantId)
        │
        ▼
tenantStore.switchTenant(newId)
  ├── PUT /auth/active-tenant ──────────────────────────────▶ Validate user is
  │                                                            member of tenant
  │                                                            Update user.active_tenant_id
  │   ◀──────────────────────────────────────────────────────── 200 OK
  │
  ├── tenantStore.fetchActiveTenant()
  │     GET /tenants/{id} ──────────────────────────────────▶ Return tenant details
  │     ◀──────────────────────────────────────────────────── { name, plan, guild_count, ... }
  │
  ├── guildStore triggered by watcher:
  │     currentGuild = null
  │     guilds = []
  │     fetchGuilds()
  │       GET /guilds ──────────────────────────────────────▶ Return guilds for new tenant
  │       ◀──────────────────────────────────────────────────── [guild1, guild2]
  │       currentGuild = guild1
  │       fetchMembers(guild1.id)
  │
  ├── calendarStore triggered by watcher:
  │     events = []
  │     (Calendar view will re-fetch on next render)
  │
  ├── usePermissions triggered by guildStore.currentGuild change:
  │     fetchPermissions()
  │       GET /roles/my-permissions/{guild_id} ─────────────▶ Return permissions
  │
  └── useSocket:
        leaveTenant(oldTenantId)
        joinTenant(newTenantId)
        leaveGuild(oldGuildId)
        joinGuild(newGuildId)
```

**Key UX considerations:**

| Concern | Solution |
|---------|----------|
| Flicker during switch | Show loading spinner/skeleton in sidebar while switching |
| User on a guild-specific page during switch | If current route requires a guild (e.g., `/raids/123`), redirect to `/dashboard` after switch (the old raid doesn't exist in new tenant) |
| Notifications during switch | Notifications are user-scoped (cross-tenant) — no change needed |
| Socket.IO reconnection | Leave old rooms, join new rooms; the socket connection itself persists |
| Browser back button after switch | Router history naturally handles this; data is already loaded for the new tenant |

---

## 12. Frontend Testing Strategy for Multi-Tenancy

### 12.1 Current Testing State

The frontend currently has **no dedicated frontend tests** (no Vitest, Cypress,
or Playwright test files). All testing is done via:
1. Backend Python tests (632+ tests via pytest) — tests API behavior
2. Manual smoke testing via the development server
3. `npx vite build` to verify no compile/type errors

### 12.2 Recommended Testing Approach for Tenancy

Given the critical nature of tenant isolation (a bug could expose User A's data
to User B), the following testing strategy is recommended:

#### 12.2.1 Component Unit Tests (Vitest)

Add Vitest for testing store logic and composable behavior:

```javascript
// tests/frontend/stores/tenant.test.js

import { setActivePinia, createPinia } from 'pinia'
import { useTenantStore } from '@/stores/tenant'

describe('Tenant Store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  test('fetchTenants sets first tenant as active', async () => { ... })
  test('switchTenant updates activeTenantId', async () => { ... })
  test('atGuildLimit returns true when at limit', () => { ... })
  test('isOwner returns true for owner role', () => { ... })
  test('reset clears all state', () => { ... })
})
```

```javascript
// tests/frontend/composables/usePermissions.test.js

describe('usePermissions (tenant)', () => {
  test('canTenant("create_guild") returns false at guild limit', () => { ... })
  test('canTenant("invite_member") returns true for tenant admin', () => { ... })
  test('canTenant("manage_settings") returns false for member', () => { ... })
  test('isTenantOwner returns true for owner role', () => { ... })
})
```

#### 12.2.2 Integration/E2E Tests (Playwright or Cypress)

Critical user flows that should be tested end-to-end:

```
Test: "Tenant switching changes data context"
1. Login as User A (owns Tenant A with Guild1, Guild2)
2. Verify sidebar shows "Tenant A" active with Guild1, Guild2
3. Accept invite to Tenant B (owned by User B with Guild3)
4. Switch to Tenant B via sidebar
5. Verify sidebar shows "Tenant B" active with Guild3 only
6. Verify calendar shows Guild3's events (not Guild1/Guild2)
7. Switch back to Tenant A
8. Verify Guild1 and Guild2 are shown again

Test: "Invite link flow"
1. Login as User A (tenant owner)
2. Navigate to /tenant/invite
3. Create invite link with max_uses=1, expires=7d
4. Copy the link
5. Open in incognito → shows "Login to Accept"
6. Register as new User B → auto-redirect to invite page
7. Accept → redirected to dashboard with Tenant A active
8. Verify User B sees Tenant A's guilds

Test: "Global admin tenant management"
1. Login as global admin
2. Navigate to /admin/global → Tenants tab
3. Verify all tenants listed with correct stats
4. Suspend a tenant → verify suspended badge
5. Try to access suspended tenant as its owner → blocked
6. Activate tenant → verify access restored
```

#### 12.2.3 Testing Priority

| Priority | Test Category | When |
|----------|--------------|------|
| 🔴 **P0** | Tenant switching changes data context | Phase 0 |
| 🔴 **P0** | Invite link create/accept flow | Phase 0 |
| 🔴 **P0** | Guild creation respects tenant limit | Phase 0 |
| 🟡 **P1** | Global admin tenant CRUD | Phase 0 |
| 🟡 **P1** | Tenant settings owner-only access | Phase 0 |
| 🟢 **P2** | Notification cross-tenant visibility | Phase 0 |
| 🟢 **P2** | Socket.IO room switching | Phase 0 |

### 12.3 Build Verification

After all frontend changes, verify:
```bash
# No build errors:
npx vite build

# No TypeScript/linting errors (if configured):
npx eslint src/ --ext .vue,.js

# Development server runs:
npm run dev
```

---

### End of Frontend Migration Plan

> **Summary:** The frontend multi-tenant migration adds **~1,720 lines** across
> **8 new files** and **12 modified files**. Most existing views (11 of 15)
> require **zero changes** because tenant context flows through the store layer
> and Axios interceptor. The heaviest changes are the new tenant store, the
> sidebar tenant switcher, the global admin TenantsTab, and three new views
> (invite accept, tenant settings, tenant invite management).

---

## 13. Cleanup Protocol — Per-Phase Code Hygiene

> **Principle:** Every phase runs on a **separate branch**. Before merging that
> branch, every line of orphaned, unused, deprecated, or shortcut code introduced
> **or made obsolete** by that phase must be removed. The branch should merge
> cleaner than it found the codebase — no trash, no dead code, no "we'll clean
> this up later" comments.

---

### 13.1 Cleanup Rules (Apply to Every Phase)

These rules are **mandatory** for every phase's PR before merge:

| # | Rule | How to Verify |
|---|------|---------------|
| 1 | **No orphaned files** — every file must be imported/used somewhere | `grep -rn "import.*{filename}"` across the codebase; unused files must be deleted |
| 2 | **No dead imports** — every `import` statement must reference something used in that file | Linter (`ruff check` / `eslint --no-unused-vars`) with zero warnings |
| 3 | **No commented-out code** — delete it, it lives in git history | `grep -rn "^#.*def \|^#.*class \|^//.*function\|^//.*const "` returns empty |
| 4 | **No TODO/FIXME/HACK/XXX in merged code** — resolve them or create a tracked issue | `grep -rn "TODO\|FIXME\|HACK\|XXX"` returns empty for changed files |
| 5 | **No temporary helpers, scripts, or workarounds** | No `/tmp/`, no `_temp_`, no `_old_` files in the repo |
| 6 | **No backward-compat shims older than 1 phase** — if Phase N introduced a shim, Phase N+1 must remove it | Review every `# backward compat` / `# compat` / `# legacy` comment |
| 7 | **No unreachable code paths** — if a condition can never be true, remove the branch | Manual review + coverage report |
| 8 | **No duplicate logic** — if the same logic exists in 2+ places, consolidate into a shared utility | `grep` for known patterns; review during code review |
| 9 | **No stale tests** — tests must test current behavior, not removed features | `pytest` passes with `--strict-markers`; no `@skip` without a linked issue |
| 10 | **No stale documentation** — docstrings and comments must match current code | Review every changed file's docstrings |
| 11 | **No stale translation keys** — if a UI element is removed, its i18n keys must be removed | Diff `translations/*.json` against actual `t('...')` usage |
| 12 | **Full build + lint + test before merge** — zero warnings, zero failures | `python -m pytest tests/ && npx vite build && npx eslint src/` |

---

### 13.2 Pre-Existing Cleanup Items (Before Phase 0)

These items exist in the codebase **today** and must be cleaned up as the
**first step** of Phase 0, before any new code is written:

| # | Item | File | Action | Reason |
|---|------|------|--------|--------|
| 1 | **Orphaned `SystemTab.vue`** | `src/components/admin/SystemTab.vue` (394 lines) | **Delete** | Not imported anywhere. Replaced by `UsersTab.vue` + `SettingsTab.vue`. Dead code. |
| 2 | **Stale tech debt list in §9.3** | `docs/saas-decoupling-plan.md` §9.3 | **Resolve or remove** | Items like "Consolidate frontend role label maps (7 duplicates)" — verify if already done, if so remove the item; if not, do it now |
| 3 | **`codebase-cleanup-plan.md` completion** | `docs/codebase-cleanup-plan.md` | **Mark completed items** | Verify which cleanup tasks are done; remove completed items or mark them ✅ |

---

### 13.3 Per-Phase Cleanup Checklists

Each phase has a specific cleanup checklist. These are **not optional** — they
are part of the phase's definition of done.

#### 13.3.1 Phase 0 Cleanup Checklist

Phase 0 introduces tenancy. It also obsoletes several pre-tenancy patterns.

**Files to delete:**

| File | Reason |
|------|--------|
| `src/components/admin/SystemTab.vue` | Orphaned; never imported. Functionality lives in `UsersTab.vue` + `SettingsTab.vue`. |

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `AppSidebar.vue` lines 33-50 | "Available guilds to join" section | **Remove** — guild discovery is now within tenant context; users join tenants first, then guilds within |
| `AppSidebar.vue` `availableGuilds` computed | Computed property filtering `allGuilds` by `allow_self_join` | **Remove** — replaced by tenant invitation system |
| `guild_service.py` `list_all_guilds()` | Lists ALL guilds in the system (no tenant filter) | **Refactor** — must filter by `tenant_id`; old global listing is a security risk |
| `guilds.py` API `GET /guilds/all` | Returns all guilds without tenant scoping | **Refactor** — scope to active tenant; global admin has separate endpoint |
| Any `console.log` / `print()` debug statements | Left from development | **Remove** — use proper logging (Python `logging` module, no `print()`) |

**Test fixtures to update:**

| Area | Action |
|------|--------|
| All test fixtures creating guilds | Add `tenant_id` parameter — tests that create guilds without a tenant context must be updated or they fail with `NOT NULL` constraint |
| All test fixtures creating events/signups | Add `tenant_id` + `guild_id` where newly required |
| `conftest.py` | Add `tenant_with_owner` and `guild_in_tenant` base fixtures (see §10.16) |

**Verification commands:**
```bash
# 1. No orphaned Vue components (every .vue file must be imported somewhere)
for f in src/components/**/*.vue; do
  name=$(basename "$f" .vue)
  if ! grep -rq "$name" src/ --include="*.vue" --include="*.js" | grep -v "$f"; then
    echo "ORPHAN: $f"
  fi
done

# 2. No dead Python imports
ruff check app/ tests/ --select F401

# 3. No dead JS imports (if eslint configured)
npx eslint src/ --rule '{"no-unused-vars": "error"}' --ext .vue,.js

# 4. Full build + test
python -m pytest tests/ -v && npx vite build

# 5. No print() statements in production code
grep -rn "^\s*print(" app/ --include="*.py" | grep -v "test"
```

#### 13.3.2 Phase 1 Cleanup Checklist

Phase 1 moves constants to expansion-specific files. Cleanup the old locations.

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `app/constants.py` | Hardcoded `WOTLK_RAIDS`, `CLASS_ROLES`, `CLASS_SPECS` | **Move** to `app/expansions/wotlk.py`; keep only re-export wrappers in `constants.py` for exactly one phase of backward compat |
| `app/constants.py` re-exports | Backward-compat imports from `constants.py` → `expansions/wotlk.py` | These are **allowed in Phase 1 only** — mark with `# COMPAT: Remove in Phase 2` comment |
| Test files | Tests importing directly from `app/constants` for class/spec data | **Update** to import from `app/expansions/` or use the new expansion registry |

**Dead code detection:**
```bash
# Find any remaining direct import of CLASS_ROLES from constants.py
grep -rn "from app.constants import.*CLASS_ROLES\|from app.constants import.*CLASS_SPECS\|from app.constants import.*WOTLK_RAIDS" app/ tests/
# Expected: only re-export wrappers in constants.py, nothing else
```

#### 13.3.3 Phase 2 Cleanup Checklist

Phase 2 replaces self-join with invitation-based guild membership.

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `Guild` model `allow_self_join` field | Boolean flag for direct join | **Deprecate** — if invitation system fully replaces it, remove the column in migration. If kept for backward compat, mark with `# DEPRECATED: Remove in Phase 3` |
| `POST /guilds/{id}/join` endpoint | Direct join without invitation | **Remove** or **gate behind invitation** — direct join should not bypass the invitation system |
| `AppSidebar.vue` `doJoinGuild()` | Direct join button in sidebar | **Remove** if direct join endpoint is removed |
| `guilds.js` API `joinGuild()` | API call for direct join | **Remove** if endpoint is removed |
| Phase 1 backward-compat re-exports | `# COMPAT: Remove in Phase 2` markers | **Remove now** — Phase 2 is where these shims die |

**Verification:**
```bash
# No references to allow_self_join in frontend (if deprecated)
grep -rn "allow_self_join\|self.join\|self_join" src/ --include="*.vue" --include="*.js"
# Expected: empty

# No direct join endpoints remaining
grep -rn "join.*guild\|guilds.*join" app/api/ --include="*.py"
# Expected: only invitation-based join
```

#### 13.3.4 Phase 3 Cleanup Checklist

Phase 3 introduces the class-role matrix, replacing static mappings.

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `app/expansions/*.py` static `CLASS_ROLES` | Static class→role mappings | **Keep as defaults** but remove any code that reads them directly for validation (should go through matrix resolver) |
| `signup_service.py` hardcoded validation | `if char.role not in CLASS_ROLES[char.wow_class]` | **Replace** with `matrix.is_valid_role(guild_id, char.wow_class, char.role)` |
| `lineup_service.py` hardcoded validation | Similar static class→role check | **Replace** with matrix resolver |
| `src/constants.js` `CLASS_ROLES` | Static frontend mapping | **Replace** with dynamic data from `GET /api/v1/guilds/{id}/class-role-matrix` |

**Verification:**
```bash
# No hardcoded CLASS_ROLES validation in services
grep -rn "CLASS_ROLES\[" app/services/ --include="*.py"
# Expected: empty (all go through matrix resolver)
```

#### 13.3.5 Phase 4 Cleanup Checklist

Phase 4 adds multi-expansion support. WotLK-only assumptions must go.

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `src/constants.js` static `WOW_CLASSES` | Hardcoded 10 WotLK classes | **Remove** — frontend gets classes from constants store which fetches from expansion-aware backend |
| `src/constants.js` static `RAID_TYPES` | Hardcoded 8 WotLK raids | **Remove** — same as above |
| `CharacterManagerView.vue` | Static class dropdown from `WOW_CLASSES` | **Replace** with `constantsStore.wowClasses` (already done but verify no hardcoded fallback) |
| `app/constants.py` | Any remaining re-exports or hardcoded expansion data | **Remove entirely** if all data lives in `app/expansions/` registry |
| Phase 1 compat shims | Anything marked `# COMPAT: Remove in Phase 4` | **Remove now** |

**Verification:**
```bash
# No hardcoded WoW class lists in frontend
grep -rn "Death Knight.*Druid.*Hunter\|WOW_CLASSES.*=.*\[" src/ --include="*.js" --include="*.vue"
# Expected: only in constants.js static defaults (used until API loads)

# No WotLK-only raid types in frontend
grep -rn "naxx\|ulduar\|icc" src/ --include="*.js" --include="*.vue" | grep -v "constants.js"
# Expected: empty (raid types come from backend)
```

#### 13.3.6 Phase 5 Cleanup Checklist

Phase 5 extracts Warmane and Discord into plugins.

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `app/services/warmane_service.py` | Direct Warmane API integration | **Move** into `app/plugins/warmane/` — delete original file |
| `app/services/discord_service.py` | Direct Discord integration | **Move** into `app/plugins/discord/` — delete original file |
| `src/api/warmane.js` | Frontend Warmane API module | **Move** into plugin dynamic loader or delete if plugin handles its own API |
| `src/api/armory.js` | Frontend armory API module | **Move** into plugin dynamic loader or delete |
| `app/api/v1/warmane.py` | Warmane blueprint | **Move** into plugin registration — delete from main API |
| `WARMANE_REALMS` in `app/constants.py` | Hardcoded Warmane realms | **Move** into Warmane plugin config; constants.py should not know about specific providers |
| `WARMANE_REALMS` in `src/constants.js` | Same, frontend side | **Remove** — realms come from active provider plugin |
| `useWowheadTooltips.js` | Inline Wowhead script injection | **Consider** moving to plugin if Wowhead integration becomes optional |

**Verification:**
```bash
# No direct Warmane/Discord imports outside plugins/
grep -rn "warmane_service\|discord_service" app/ --include="*.py" | grep -v "plugins/"
# Expected: empty

# No Warmane/armory API modules in frontend (if moved to plugins)
ls src/api/warmane.js src/api/armory.js 2>/dev/null
# Expected: files don't exist
```

#### 13.3.7 Phase 6 Cleanup Checklist

Phase 6 adds billing. Clean up hardcoded plan defaults.

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `Tenant` model `max_guilds` default=3, `max_members` default=50 | Hardcoded limits | **Replace** with limits from billing/subscription model. Defaults should come from plan definition, not model defaults |
| `tenant_service.py` guild limit check | `if guild_count >= tenant.max_guilds` | **Replace** with `billing_service.check_limit(tenant, 'guilds')` if billing manages limits |
| Phase 0 manual limit checks | Anywhere `tenant.max_guilds` is checked directly | **Consolidate** into billing service |

**Final full-codebase audit (see §13.4):**
```bash
# Run all verification commands from all previous phases
# Confirm zero orphans, zero dead imports, zero stale tests
```

---

### 13.4 Dead Code Detection Process

Run this process **at the end of every phase** and **before every merge**:

#### 13.4.1 Backend (Python)

```bash
# ── Step 1: Dead imports ──
ruff check app/ tests/ --select F401 --output-format text
# Fix ALL F401 (unused import) warnings

# ── Step 2: Unused functions ──
# Use vulture (dead code finder) or manual grep:
pip install vulture
vulture app/ --min-confidence 80
# Review each finding — false positives are common with Flask/SQLAlchemy

# ── Step 3: Unreferenced files ──
# Every .py file in app/ should be imported by something:
for f in $(find app/ -name "*.py" ! -name "__init__.py" ! -name "__pycache__"); do
  module=$(echo "$f" | sed 's|/|.|g' | sed 's|\.py$||')
  if ! grep -rq "$(basename $f .py)" app/ --include="*.py" | grep -v "$f"; then
    echo "POSSIBLY UNUSED: $f"
  fi
done

# ── Step 4: print() statements (should use logging) ──
grep -rn "^\s*print(" app/ --include="*.py"
# Expected: empty for production code

# ── Step 5: Commented-out code ──
grep -rn "^#\s*def \|^#\s*class \|^#\s*from \|^#\s*import " app/ --include="*.py"
# Expected: empty

# ── Step 6: TODO/FIXME markers ──
grep -rn "TODO\|FIXME\|HACK\|XXX\|TEMP\|DEPRECATED" app/ --include="*.py"
# Expected: empty (create tracked issues instead)
```

#### 13.4.2 Frontend (JavaScript/Vue)

```bash
# ── Step 1: Dead imports (ESLint) ──
npx eslint src/ --rule '{"no-unused-vars": "error", "no-unused-imports": "error"}' --ext .vue,.js

# ── Step 2: Orphaned components ──
for f in $(find src/components/ -name "*.vue"); do
  name=$(basename "$f" .vue)
  count=$(grep -rl "$name" src/ --include="*.vue" --include="*.js" | grep -v "$f" | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "ORPHAN: $f"
  fi
done

# ── Step 3: Orphaned API modules ──
for f in src/api/*.js; do
  name=$(basename "$f" .js)
  if [ "$name" = "index" ]; then continue; fi
  count=$(grep -rl "@/api/$name\|from.*api/$name" src/ --include="*.vue" --include="*.js" | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "ORPHAN API: $f"
  fi
done

# ── Step 4: Orphaned composables ──
for f in src/composables/*.js; do
  name=$(basename "$f" .js)
  count=$(grep -rl "$name" src/ --include="*.vue" --include="*.js" | grep -v "$f" | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "ORPHAN COMPOSABLE: $f"
  fi
done

# ── Step 5: Unused i18n keys ──
# Compare keys in translations/en.json with actual t('...') usage:
# (Manual audit or use a tool like i18n-unused)

# ── Step 6: Build verification ──
npx vite build
# Must succeed with zero warnings
```

#### 13.4.3 Tests

```bash
# ── All tests pass ──
python -m pytest tests/ -v --tb=short

# ── No skipped tests without reason ──
python -m pytest tests/ -v | grep -i "skip\|xfail"
# Review each skip — should have a linked issue or be removed

# ── No tests for removed features ──
# Manual review: if a feature was removed in this phase, its tests should
# also be removed (not skipped).
```

---

### 13.5 Branch Hygiene

Since each phase is developed on a **separate branch**, these branch rules
apply:

| Rule | Details |
|------|---------|
| **Feature branch naming** | `phase-0/tenancy`, `phase-1/expansion-registry`, etc. |
| **No merge without cleanup** | PR cannot be approved until all cleanup checklist items are checked off |
| **No "fix later" comments** | If something can't be fixed now, create a GitHub issue and link it; do NOT leave a TODO in code |
| **Squash-merge or rebase** | Keep commit history clean; no "fix typo" / "oops" commits in main |
| **Delete branch after merge** | Feature branches are deleted after merge to main/develop |
| **No cross-phase debt** | Each phase's cleanup checklist must be complete before starting the next phase. No carrying forward cleanup debt. |

---

### 13.6 Definition of Done (Per Phase)

A phase is **done** only when ALL of the following are true:

- [ ] All feature checkboxes in §7 for this phase are checked
- [ ] All cleanup checkboxes in §13.3.X for this phase are checked
- [ ] Dead code detection (§13.4) returns zero findings
- [ ] `python -m pytest tests/ -v` — all tests pass, zero skipped without issue
- [ ] `npx vite build` — zero warnings, zero errors
- [ ] `ruff check app/` — zero linting issues (or pre-existing baseline unchanged)
- [ ] Code review approved by at least one reviewer
- [ ] No `TODO`/`FIXME`/`HACK`/`XXX` in changed files
- [ ] No orphaned files, dead imports, or commented-out code
- [ ] Documentation (docstrings, comments, this plan) updated to reflect current state
- [ ] Translation files updated (no stale keys, no missing keys)
- [ ] PR description lists every file changed with a one-line rationale

---

### 13.7 Known Pre-Existing Items to Track

Items that exist today and should be addressed **no later than** the indicated
phase:

| # | Item | Current State | Address By | Action |
|---|------|---------------|------------|--------|
| 1 | `SystemTab.vue` (394 lines) | Orphaned — not imported anywhere | **Phase 0** | Delete |
| 2 | `codebase-cleanup-plan.md` | Contains cleanup tasks — unclear which are done | **Phase 0** | Audit; mark completed items ✅; create issues for remaining |
| 3 | `allow_self_join` on Guild model | Active — used in sidebar for direct guild join | **Phase 2** | Remove or deprecate when invitation system replaces it |
| 4 | Static `WOW_CLASSES` in `src/constants.js` | Active — hardcoded 10 WotLK classes | **Phase 4** | Remove when constants store fetches expansion-aware data |
| 5 | Static `WARMANE_REALMS` in `src/constants.js` + `app/constants.py` | Active — hardcoded Warmane realm list | **Phase 5** | Remove when provider plugins manage realm lists |
| 6 | `i18n-plan.md` | Planning doc — may become stale | **Phase 0** | Review; integrate remaining items into this plan or archive |
| 7 | Hardcoded `max_guilds=3`, `max_members=50` on Tenant model | Will be introduced in Phase 0 | **Phase 6** | Replace with billing-managed limits |
