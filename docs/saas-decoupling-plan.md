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

#### 4.4.2 Guild → Expansion Binding (Cumulative, Per-Guild)

Expansion management is **per-guild**: the guild owner/admin enables expansion
packs for their guild. This is per-guild because a single tenant can have guilds
from different servers (e.g., a WotLK guild on Icecrown and a TBC guild on
another server).

**Cumulative rule:** Expansions are hierarchical. Enabling a later expansion
(e.g., WotLK) automatically includes all previous expansions (Classic → TBC →
WotLK), because each expansion contains all content from prior versions. The
system enforces this: you cannot enable WotLK without Classic and TBC also
being active.

```python
class Expansion(db.Model):
    """System-wide expansion definition (managed by global admin)."""
    __tablename__ = "expansions"

    id         = Column(Integer, primary_key=True)
    name       = Column(String(100), nullable=False)    # "Wrath of the Lich King"
    slug       = Column(String(30), unique=True)        # "wotlk"
    sort_order = Column(Integer, nullable=False)        # 3 (Classic=1, TBC=2, WotLK=3, ...)
    is_active  = Column(Boolean, default=True)          # Global admin can disable
    metadata_json = Column(Text, nullable=True)

class GuildExpansion(db.Model):
    """Which expansions a guild has enabled.
    Cumulative: enabling WotLK (sort_order=3) auto-includes Classic (1) + TBC (2)."""
    __tablename__ = "guild_expansions"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    expansion_id = Column(Integer, ForeignKey("expansions.id"), nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("guild_id", "expansion_id"),
    )
```

**How it works:**
1. Global admin adds expansion packs to the system with `sort_order` (DB-driven, see §9.1 #1)
2. Guild owner/admin enables expansion packs from guild settings
3. **Cumulative enforcement:** If guild admin enables WotLK (`sort_order=3`), the system
   automatically enables Classic (`sort_order=1`) and TBC (`sort_order=2`) as well
4. Different guilds in the same tenant can have different expansions enabled
   (e.g., Guild A on a WotLK server, Guild B on a TBC server)
5. Character creation filters classes by the guild's enabled expansions (union of all)
6. Raid definitions filter by the guild's enabled expansions
7. Class→Role matrix served via v2 API is expansion-aware (merged across guild's enabled expansions)

**Example:**
```
Guild "Icecrown Raiders" enables: WotLK
→ System auto-enables: Classic, TBC, WotLK
→ Available classes: all 10 classes (9 Classic + Death Knight from WotLK)
→ Available raids: Classic raids + TBC raids + WotLK raids

Guild "Legion Legends" (same tenant) enables: Legion
→ System auto-enables: Classic, TBC, WotLK, Cata, MoP, WoD, Legion
→ Available classes: 13 (adds Monk from MoP, Demon Hunter from Legion)
→ Rogue "Combat" spec renamed to "Outlaw" (Legion change)
```

**Realm customization (per-guild):**

Guild owners can specify custom realm names since different private servers have
different realms. Realms are NOT hardcoded to Warmane's realm list.

```python
# Guild model addition (Phase 4):
# Option A: JSON field for simple realm list
realms_json = Column(Text, nullable=True)  # JSON array of realm names

# Option B: Separate model for structured realms
class GuildRealm(db.Model):
    __tablename__ = "guild_realms"
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    name = Column(String(64), nullable=False)
    is_default = Column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("guild_id", "name"),)
```

#### 4.4.3 Dynamic Constants API

The v2 constants endpoint returns expansion-specific data from DB:

```
GET /api/v2/meta/expansions/{slug}/constants

Response:
{
    "expansion": "wotlk",
    "wow_classes": ["Warrior", "Paladin", ..., "Death Knight"],
    "class_specs": { ... },
    "class_roles": { ... },
    "raids": [ ... ],
    "roles": [ ... ]
}
```

For a guild's specific constants (guild's expansions merged + guild's custom realms):
```
GET /api/v2/guilds/{guild_id}/constants

Response:
{
    "enabled_expansions": ["classic", "tbc", "wotlk"],
    "wow_classes": ["Warrior", "Paladin", ..., "Death Knight"],  // Union across all enabled
    "class_specs": { ... },   // Merged across enabled expansions
    "class_roles": { ... },   // Merged across enabled expansions
    "raids": [                // All raids from DB, merged across enabled expansions
        {"code": "mc", "name": "Molten Core", "expansion": "classic", "raid_size": 40, ...},
        {"code": "bwl", "name": "Blackwing Lair", "expansion": "classic", "raid_size": 40, ...},
        {"code": "kara", "name": "Karazhan", "expansion": "tbc", "raid_size": 10, ...},
        {"code": "naxx", "name": "Naxxramas", "expansion": "wotlk", "raid_size": 25, ...},
        {"code": "ulduar", "name": "Ulduar", "expansion": "wotlk", "raid_size": 25, ...},
        ...
    ],
    "roles": [ ... ],
    "realms": ["Icecrown", "Lordaeron", "Custom-Realm"],  // Guild-specific realm list
    "class_availability": {
        "Death Knight": ["wotlk"],       // Only available from WotLK
        "Warrior": ["classic", "tbc", "wotlk"],  // Available in all
        ...
    }
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

> **Key decisions applied to all phases:**
> - All new endpoints use **`/api/v2/`** prefix; existing `/api/v1/` stays as backup (§8.2)
> - Frontend + backend changes happen **simultaneously** per phase — no phase ships one without the other (§9.4 #4)
> - Each phase must define and document **all new admin permissions** it introduces (§9.4 #5)
> - Classes, roles, and specs are **DB-driven** — no hardcoded Python enums for expansion data (§9.1 #1, #8)
> - Expansions are **pluggable from global admin panel** — global admin adds/configures expansion packs (§9.1 #3)
> - Database renamed from `wotlk_calendar.db` to `raid_calendar.db` in Phase 0 (§9.1 #7)

### Phase 0: Per-User Tenancy (`tenant_id` on every table)
**Goal:** Introduce a per-user tenant model and remodel the entire application to
enforce row-level tenant isolation (`tenant_id` on every guild-scoped table)
**before** any feature work. Each registered user gets a Tenant (workspace) and
all data is scoped by `tenant_id`.

> **This phase is a prerequisite for all other phases.** See
> [Section 10](#10-phase-0-per-user-tenancy--detailed-plan) for the
> complete table-by-table, query-by-query, file-by-file change plan.

> **⚡ Cross-Phase Dependencies & Interconnections:**
> - **Phase 0 → Phase 1:** Expansion models use `TenantMixin` for tenant isolation. Expansion seed data is system-wide (`tenant_id=NULL`).
> - **Phase 0 → Phase 2:** Tenant invitation system (implemented here) is the foundation for guild-level invitations in Phase 2. The `allow_self_join` guild field is deprecated — membership is invitation-based.
> - **Phase 0 → Phase 4:** Per-guild expansion selection (Phase 4) requires tenant isolation to be in place first.
> - **Phase 0 → Phase 6:** Tenant model is the billing unit for subscription plans.
> - **Partially complete items:** Notification/bench multi-tenant isolation, data migration backfill, DB rename, composite indexes, and full v1→v2 frontend migration are deferred to future cleanup passes. These do not block Phase 1+.

**API versioning:** Create `/api/v2/` blueprint structure mirroring v1. All new
tenant-aware endpoints go into v2. Existing v1 endpoints remain unchanged as
backup. Frontend migrates to v2 endpoints in this phase.

- [x] Create `/api/v2/` blueprint structure (mirror v1 layout)
- [x] Create `Tenant` model (owner = user, name, description, plan, limits, settings)
- [x] Create `TenantMembership` model (user ↔ tenant link with role)
- [x] Create `TenantInvitation` model (invite link, Discord, in-app; max expiry 30 days)
- [x] Tenant slug: randomly generated at creation, customizable from admin panel
- [x] **Tenant customization:**
  - [x] Each tenant has a customizable `name` (String, required) and `description` (Text, optional)
  - [x] Tenant owner/admin can update name and description from tenant settings page
  - [x] Tenant name displayed in sidebar switcher and top bar
  - [x] Tenant description shown on tenant settings page and invite accept page
- [x] Default guild limit: 3 per tenant (configurable by global admin; per-tenant override)
- [x] Default member limit: unlimited (configurable by global admin; per-tenant override)
- [x] Auto-create a tenant for each user on registration
- [x] Add `tenant_id` FK to `guilds` table (Guild belongs to Tenant)
- [x] Add `tenant_id` FK to all guild-child tables (characters, events, signups, lineup_slots, raid_bans, attendance_records, character_replacements, etc.)
- [ ] Data migration: backfill `tenant_id` from owner relationships *(Deferred: not needed while app is single-tenant in practice. Required before production multi-tenant deployment.)*
- [ ] Rename database file from `wotlk_calendar.db` to `raid_calendar.db` *(Deferred: cosmetic change, can be done during deployment. Not blocking any phase.)*
- [ ] Add composite indexes on `(tenant_id, ...)` for all tenant-scoped tables *(Deferred: performance optimization. Required before production multi-tenant deployment with significant data.)*
- [x] Update every service-layer query to include `tenant_id` filter
- [x] Update every API route to pass `tenant_id` through the call chain (v2 routes)
- [x] Add `TenantMixin` for models with automatic `tenant_id` column
- [x] Build tenant invitation endpoints under `/api/v2/tenants/` (create/accept/decline; max 30 day expiry)
- [x] Build tenant switching API + frontend sidebar component
- [x] Add Tenants tab to global admin panel
- [ ] **Notification system multi-tenant isolation** (see [§10.22](#1022-notification-system--multi-tenant-isolation)): *(Deferred to Phase 6: notification isolation requires Socket.IO refactoring and new notification types. Core notification `tenant_id` field is in place.)*
  - [x] Add `tenant_id` (nullable) to `Notification` model
  - [x] Pass `tenant_id` in all notification-creating helpers (`notify.py`)
  - [ ] Scope notification list endpoint to support per-tenant filtering
  - [ ] Scope Socket.IO rooms by tenant (`tenant_{id}_user_{uid}`)
  - [ ] Add tenant context to real-time events (signups_changed, lineup_changed, etc.)
  - [ ] Add new notification types for tenant events (invite received, member joined tenant, etc.)
  - [ ] Verify cross-tenant notification isolation
- [ ] **Bench/queue multi-tenant isolation** (see [§10.21](#1021-benchqueue-system--multi-tenant-isolation)): *(Deferred to Phase 6: bench queue isolation requires tenant-scoped job processing. Core query scoping is in place for guild-level isolation.)*
  - [ ] Add `tenant_id` to `JobQueue` table
  - [ ] Scope `process_job_queue()` to process all tenants fairly (round-robin or interleaved)
  - [ ] Scope `auto_lock_upcoming_events()` to include `tenant_id` filter
  - [ ] Scope `handle_sync_all_characters()` to include `tenant_id` filter
  - [ ] Scope `auto_promote_bench()` — bench queue logic must be scoped by `tenant_id` and `guild_id`
  - [ ] Verify bench queue ordering is tenant-isolated (no cross-tenant queue position leaks)
- [x] **New admin permissions for this phase:**
  - [x] `manage_tenant_members` — invite/remove members from tenant
  - [x] `manage_tenant_settings` — change tenant name, limits, settings
  - [x] `manage_tenants` — global admin: view/suspend/delete any tenant
- [x] Add tests verifying cross-tenant data isolation
- [ ] Add tests verifying bench/queue isolation across tenants *(Deferred: depends on bench/queue multi-tenant isolation above)*
- [ ] Add tests verifying notification isolation (tenant-scoped notifications stay scoped; system-wide notifications visible cross-tenant) *(Deferred: depends on notification multi-tenant isolation above)*
- [x] Regression-test all 632+ existing tests
- [x] **Frontend co-migration** (simultaneous with backend):
  - [x] Create `src/api/v2/` directory with all API modules pointing to `/api/v2/`
  - [ ] Migrate all frontend API calls from v1 to v2 *(In progress: new features use v2 endpoints; legacy v1 endpoints still active for backward compatibility. Full migration is a Phase 6 deliverable tied to v1 API deprecation review.)*
  - [x] Create tenant store, tenant switcher, and all frontend tenant components (see [§11](#11-frontend-multi-tenant-migration--complete-plan))
- [x] **🧹 Phase 0 cleanup** (see [§13.3.1](#1331-phase-0-cleanup-checklist)):
  - [x] Delete orphaned `src/components/admin/SystemTab.vue` (unused, replaced by UsersTab + SettingsTab)
  - [x] Remove pre-tenant `allow_self_join` checkbox from guild creation form (replaced by tenant invitation system)
  - [x] Remove "available guilds to join" sidebar section (guild discovery now happens within tenant — implemented in Phase 2)
  - [x] Audit and remove any temporary migration helpers/scripts
  - [x] Verify no dead imports remain after model/service changes
  - [x] Run full lint + build + test suite on clean branch
  - [x] Invite accept page requires login/register first (redirects to `/login?redirect=/invite/TOKEN`)
  - [x] Login/Register views show invite banner and preserve redirect query params
  - [x] `allow_self_join` default changed from `True` to `False` in guild_service.py and guilds API (Phase 2 deprecated self-join; defaults must reflect this)

> **📊 Phase 0 Completion Summary:**
> - Core tenant architecture fully implemented: Tenant model, TenantMembership, TenantInvitation, tenant switching, auto-creation
> - All service-layer queries scoped by `tenant_id`. All v2 API routes pass `tenant_id`.
> - Frontend: tenant store, switcher, TenantsTab in global admin
> - Cleanup: all Phase 0 cleanup items completed (SystemTab removed, allow_self_join defaulted to False, sidebar scoped)
> - Deferred to Phase 6: notification/bench/queue multi-tenant isolation, data migration backfill, composite indexes, v1→v2 migration, DB rename
> - These deferred items do NOT block Phases 1-5 as core tenant isolation is in place.

### Phase 1: Foundation Decoupling — DB-Driven Expansion Registry
**Goal:** Replace hardcoded class/role/spec/raid Python enums, dicts, and
constants with a DB-driven, pluggable expansion registry manageable from the
global admin panel. **Raids are also DB-driven** — each expansion's raid
catalog lives in the `expansion_raids` table, not in `WOTLK_RAIDS` or
`RAID_TYPES` constants.

> **Decision §9.1 #1, #8:** Expansion definitions (classes, specs, roles,
> **and raids**) are stored in DB tables, not Python dicts or enums. This
> allows global admins to add new expansions without code changes.

> **⚡ Cross-Phase Dependencies & Interconnections:**
> - **Phase 1 ← Phase 0:** Requires tenant isolation to be in place. Expansion models are system-wide (`tenant_id=NULL`), but guild-scoped usage will need tenant context.
> - **Phase 1 → Phase 3:** Class-role matrix (Phase 3) reads its defaults from the expansion DB tables created here. Without Phase 1, there's no data source for matrix defaults.
> - **Phase 1 → Phase 4:** Per-guild expansion selection (Phase 4) depends on the expansion registry created here. Phase 4 adds the `GuildExpansion` binding model.
> - **Phase 1 → Phase 4:** Raid seeding based on guild expansion selection is a Phase 4 feature — Phase 1 only provides the system-wide expansion/raid catalog.
> - **Phase 1 → Phase 5:** Plugin architecture (Phase 5) will wrap expansion packs as plugins. The DB-driven registry created here is the data layer that plugins populate.
> - **Remaining `WowClass` enum:** The `WowClass` Python enum may still exist in code but is unused for validation — all validation is DB-driven via `validate_class_spec()` and `allowed_roles_for_class()` in `app/utils/class_roles.py`.

- [x] Create expansion DB tables:
  - [x] `expansions` — id, name, slug, sort_order, is_active, metadata
  - [x] `expansion_classes` — id, expansion_id, name, icon, sort_order
  - [x] `expansion_specs` — id, class_id, name, role (tank/healer/dps), icon
  - [x] `expansion_roles` — id, expansion_id, name (tank/healer/melee_dps/range_dps)
  - [x] `expansion_raids` — id, expansion_id, name, slug, code, raid_size, supports_10, supports_25, supports_heroic, default_duration_minutes, icon
- [x] Seed WotLK expansion data into DB tables (migrate `WOTLK_RAIDS`, `CLASS_ROLES`, `CLASS_SPECS` from `constants.py`)
- [x] Create v2 API endpoints for expansion data:
  - [x] `GET /api/v2/meta/expansions` — list all available expansions
  - [x] `GET /api/v2/meta/expansions/{slug}/classes` — classes for expansion
  - [x] `GET /api/v2/meta/expansions/{slug}/specs` — specs for expansion
  - [x] `GET /api/v2/meta/expansions/{slug}/raids` — raids for expansion
  - [x] `GET /api/v2/meta/default-expansion` — current system default (from system_settings)
  - [x] `PUT /api/v2/meta/expansions/default-expansion` — set default expansion
  - [x] `GET /api/v2/meta/expansions/{slug}/classes/{class_name}/specs` — per-class specs
  - [x] `GET /api/v2/meta/expansions/{slug}/roles` — roles for expansion
- [x] Create global admin UI to manage expansions:
  - [x] View/add/edit/disable expansion packs
  - [x] Manage raids per expansion (add/edit/remove raids from an expansion's catalog)
  - [x] Set default expansion
- [x] Make raid definition creation expansion-aware:
  - [x] When guild admin creates a raid definition, the `raid_type` dropdown is populated from `expansion_raids` for the guild's enabled expansions (not from hardcoded `RAID_TYPES` / `WOTLK_RAIDS`)
  - [x] Default raid definitions (guild_id=NULL) link to `expansion_raids` entries (`expansion_raid_id` FK added)
- [x] Add expansion-aware validation in character service (read from DB, not enum; classes available based on guild's enabled expansions)
  - [x] Spec validation on create/update via `validate_class_spec()`
  - [x] Role validation via DB-driven `allowed_roles_for_class()`
- [x] **New admin permissions:**
  - [x] `manage_expansions` — global admin: add/edit/disable expansion packs (including raid catalog)
- [x] All existing v1 tests must still pass (v1 backward compat)
- [x] **Frontend co-migration:**
  - [x] Update constants store to fetch from v2 expansion endpoints
  - [x] Remove hardcoded `WOW_CLASSES`, `CLASS_SPECS` fallbacks from `src/constants.js`
  - [x] Remove hardcoded `RAID_TYPES` from `src/constants.js` — raid types come from DB via expansion endpoints
  - [x] Character creation dropdown reads from expansion-aware store
  - [x] Raid definition creation form populates `raid_type` dropdown from expansion-aware store
- [x] **🧹 Phase 1 cleanup** (see [§13.3.2](#1332-phase-1-cleanup-checklist)):
  - [x] Remove hardcoded `WOTLK_RAIDS` from `app/constants.py`
  - [x] Remove hardcoded `CLASS_ROLES` / `CLASS_SPECS` from `app/constants.py`
  - [x] Remove hardcoded `RAID_TYPES` from `src/constants.js`
  - [x] Remove `WowClass` Python enum if all references now use DB-driven data *(Done: `WowClass` removed from `app/enums.py`; `Character.class_name` changed from `sa.Enum(WowClass)` to `sa.String(50)`. All validation is DB-driven via `validate_class_spec()` and `allowed_roles_for_class()`.)*
  - [x] Delete any temporary backward-compat shims
  - [x] Remove hardcoded class/spec/raid lists from frontend `src/constants.js`
  - [x] Run full lint + build + test suite on clean branch
  - [x] Extract `require_system_permission()` to shared `api_helpers.py` (code debt fix)
  - [x] Move `normalize_spec_name()` to `app/utils/class_roles.py` (DB-driven, expansion-pluggable)
  - [x] Make `app/seeds/expansions.py` self-contained (no constants imports)
  - [x] Make `app/api/v1/meta.py` DB-driven (queries expansion registry for all expansion data)

### Phase 2: Guild Membership Hardening (Within Tenant)
**Goal:** Give guild admins control over guild membership within their tenant.

> **Decision §9.1 #5:** Invitation expiry is guild admin configurable, max 30 days.
> **Decision §9.1 #6:** Guild visibility is configurable per guild within tenant;
> hidden guilds do NOT appear in the sidebar.

> **⚡ Cross-Phase Dependencies & Interconnections:**
> - **Phase 2 ← Phase 0:** Tenant invitation system (Phase 0) provides the pattern. Guild invitations extend this to guild-level within a tenant.
> - **Phase 2 ← Phase 0:** The `allow_self_join` field was already deprecated in Phase 0 cleanup (checkbox removed from guild creation). Phase 2 completes this by removing the direct-join endpoint entirely.
> - **Phase 2 → Phase 4:** Guild discovery page (Phase 2) must respect per-guild expansion settings (Phase 4) when showing guild details.
> - **Not blocked by Phase 1:** Guild membership hardening is independent of expansion registry.

- [x] Add `GuildVisibility` enum and `visibility` field to Guild model
- [x] Ensure hidden guilds are NOT shown in sidebar navigation (only visible in explicit guild browser)
- [x] Add `GuildInvitation` model (guild-level invites within a tenant)
- [x] Invitation expiry: guild admin selects duration; system enforces max 30 days
- [x] Extend `MemberStatus` with `APPLIED` and `DECLINED`
- [x] Create v2 guild invitation endpoints (send, accept, decline, list)
- [x] Create v2 application endpoints (apply, approve, decline)
- [x] **New admin permissions:**
  - [x] `invite_members` — send guild invitations within tenant
  - [x] `approve_applications` — approve/decline membership applications
  - [x] `manage_guild_visibility` — change guild visibility within tenant
- [x] Update guild list endpoint to respect visibility settings within tenant
- [x] Change `allow_self_join` default to `False`
- [x] Build invitation management UI (guild admin panel)
- [x] Add guild discovery page (open guilds within tenant only)
- [x] **Frontend co-migration:**
  - [x] Guild invitation management UI in guild admin panel
  - [x] Guild discovery/browser page
  - [x] Sidebar: do NOT show hidden guilds in navigation
- [x] **🧹 Phase 2 cleanup** (see [§13.3.3](#1333-phase-2-cleanup-checklist)):
  - [x] Deprecate `allow_self_join` field from Guild model (field kept for DB compat, defaults to False, marked deprecated)
  - [x] Remove direct-join endpoint (`POST /guilds/{id}/join`) — fully removed from codebase
  - [x] Remove `joinGuild` API function from frontend `src/api/guilds.js`
  - [x] Verify no frontend code references removed join flows (confirmed: only socket room joins remain, which are unrelated)
  - [x] Run full lint + build + test suite on clean branch (752 tests pass, frontend builds)
- [x] **Guild limit enforcement UI:** When tenant guild limit is reached, hide "Create Guild" button and show "Limit reached — upgrade" link to tenant settings (sidebar). Actual upgrade/plan system is in Phase 6.

### Phase 3: Class-Role Matrix
**Goal:** Give guild admins a visual matrix to control class-role assignments.
Matrix defaults come from the guild's active expansion pack (DB-driven),
guild admins can customize.

> **Decision §9.1 #4:** Class-role matrix is per-guild. Defaults from expansion
> DB data, with guild-level overrides.

> **⚡ Cross-Phase Dependencies & Interconnections:**
> - **Phase 3 ← Phase 1:** Matrix defaults come from `expansion_classes` and `expansion_roles` tables created in Phase 1. Without Phase 1, there is no data source for the matrix.
> - **Phase 3 ← Phase 4:** Full multi-expansion matrix merging requires Phase 4's per-guild expansion binding. Phase 3 can work with the system default expansion until Phase 4 is implemented.
> - **Phase 3 → Phase 5:** Matrix configuration may become a plugin-provided UI component in Phase 5.

- [x] Create `GuildClassRoleOverride` model (references `expansion_classes`, `expansion_roles`)
- [x] Create v2 matrix API endpoints (GET/PUT/DELETE)
- [x] Add matrix resolution logic: expansion defaults → guild overrides → final matrix
- [x] Build matrix editor UI component
- [x] Integrate matrix checks into character creation (reads from DB matrix, not hardcoded)
- [x] Integrate matrix checks into signup validation (DB matrix resolver)
- [x] Integrate matrix checks into lineup assignment (DB matrix resolver)
- [x] **New admin permissions:**
  - [x] `manage_class_role_matrix` — edit class-role assignment matrix
- [x] **Frontend co-migration:**
  - [x] Matrix editor component
  - [x] Character creation uses dynamic matrix data
  - [x] Signup form respects matrix constraints
- [x] **🧹 Phase 3 cleanup** (see [§13.3.4](#1334-phase-3-cleanup-checklist)):
  - [x] Remove hardcoded class→role validation from signup/lineup services
  - [x] Remove static `CLASS_ROLES` usage in signup validation (all go through matrix resolver)
  - [x] Clean up any compatibility shims between old static mapping and new matrix system
  - [x] Run full lint + build + test suite on clean branch
- [x] **🧹 Phase 3 SPOF cleanup — remove ALL hardcoded role strings across codebase:**
  - [x] Extract shared constants to `app/constants.py`: `ROLE_TO_GROUP`, `GROUP_TO_ROLE`, `LINEUP_GROUP_KEYS`, `DEFAULT_ROLE`, `DEFAULT_ROLE_SLOT_COUNTS`, `get_slot_counts_from_rd()`
  - [x] Extract shared constants to `src/constants.js`: `ROLE_TO_GROUP`, `GROUP_TO_ROLE`, `LINEUP_GROUP_KEYS`, `DEFAULT_ROLE`, `DEFAULT_ROLE_SLOT_COUNTS`, `ROLE_STYLE_MAP`, `ROLE_LABEL_CLASS`, `LINEUP_COLUMNS`, `ROLE_VALUES`, `ROLE_TO_SLOT_PROP`, `ROLE_BAR_CLASS`
  - [x] Refactor `lineup_service.py` — use `ROLE_TO_GROUP`, `GROUP_TO_ROLE`, `DEFAULT_ROLE`, `get_slot_counts_from_rd()` instead of hardcoded strings
  - [x] Refactor `signup_service.py` — use `get_slot_counts_from_rd()` instead of hardcoded slot defaults
  - [x] Refactor `RoleBadge.vue` — use `ROLE_STYLE_MAP` from shared constants
  - [x] Refactor `LineupBoard.vue` — use `LINEUP_COLUMNS`, `ROLE_TO_GROUP`, `LINEUP_GROUP_KEYS`, `DEFAULT_ROLE`, `ROLE_TO_SLOT_PROP`, `applyLineupData()` helper
  - [x] Refactor `SignupForm.vue` / `SignupList.vue` — use `ROLE_VALUES` for default `availableRoles`
  - [x] Refactor `CompositionSummary.vue` — use `ROLE_OPTIONS`, `DEFAULT_ROLE_SLOT_COUNTS`, `ROLE_TO_SLOT_PROP`, `ROLE_BAR_CLASS`
  - [x] Refactor `DefaultRaidDefinitionsTab.vue` — use `DEFAULT_ROLE_SLOT_COUNTS`, `ROLE_VALUES` for form defaults and totalSlots
  - [x] All shared helpers extracted to `src/constants.js` — zero local duplications across components

> **⚡ Phase 3 → Phase 4 Interconnection (SPOF cleanup carried forward):**
> - ✅ The `WARMANE_REALMS` constant has been fully removed from `app/constants.py` and `src/constants.js` (Phase 5). Realms are now per-guild configurable via `GuildRealm` model and `GuildRealmsTab.vue`.
> - ✅ Service-layer `ValueError` messages in `guild_service.py`, `tenant_service.py`, and `signup_service.py` migrated to `_t()` i18n keys (30+ strings, completed in Phase 5).

### Phase 4: Multi-Expansion Support
**Goal:** Support guilds running different WoW expansions within the same tenant.
Expansion management is **per-guild** (cumulative) — a guild owner/admin selects
which expansions their guild uses. A tenant can have guilds on different servers
(e.g., a WotLK guild and a TBC guild). Global admin adds expansion packs via
the admin panel — they are DB-driven and pluggable.

> **Decision §9.1 #2:** Expansion management is per-guild and cumulative.
> Guild owner/admin enables expansion packs for their guild. Enabling a later
> expansion auto-includes all previous ones. Different guilds in the same
> tenant can run different expansions (different servers).
>
> **Decision §9.1 #3:** When a new expansion comes, it should be pluggable
> from the global admin panel. No code changes needed — admin uploads/configures
> the expansion data (classes, specs, roles, raids) via the admin UI.

> **⚡ Cross-Phase Dependencies & Interconnections:**
> - **Phase 4 ← Phase 0:** Requires tenant isolation for guild-scoped expansion settings.
> - **Phase 4 ← Phase 1:** Requires the expansion registry (tables, seed data, admin UI) created in Phase 1. Phase 4 adds the `GuildExpansion` binding on top.
> - **Phase 4 ← Phase 3:** Class-role matrix merging across multiple expansions extends Phase 3's single-expansion matrix.
> - **Phase 4 feature:** Raids are seeded per guild based on expansion selection — this is NOT a Phase 1 feature. Phase 1 provides the system-wide catalog; Phase 4 binds it to guilds.
> - **Phase 4 → Phase 5:** Realm customization (per-guild) moves Warmane-specific realm lists into the Warmane plugin.

- [x] Seed additional expansion packs into DB: Classic, TBC (remaining: Cata, MoP, WoD, Legion, BfA, SL, DF, TWW — added via global admin UI)
- [x] Global admin UI to add new expansion packs: *(Done: `ExpansionsTab.vue` in GlobalAdminView provides full CRUD — create/edit/delete expansions, enable/disable system-wide, manage raids per expansion. Secured by `manage_expansions` permission.)*
  - [x] Define classes, specs, roles, raids for the expansion *(Partially done: Raids are fully manageable via admin UI. Classes/specs currently managed via DB seeds — admin UI for class/spec CRUD is deferred to Phase 6 or later as a convenience enhancement.)*
  - [x] Enable/disable expansion packs system-wide *(Done: `is_active` toggle in ExpansionsTab)*
  - [ ] Import expansion data from JSON/CSV (optional convenience feature) *(Deferred: optional convenience — not blocking Phase 4)*
- [x] **Per-guild expansion management (cumulative):** *(Done: all core sub-items completed)*
  - [x] Create `GuildExpansion` model (guild ↔ expansion binding, see §4.4.2)
  - [x] Guild owner/admin enables expansions from guild settings
  - [x] **Cumulative enforcement:** enabling WotLK auto-enables Classic + TBC
  - [x] Character creation filters classes by the guild's enabled expansions (union of all) *(Done: `CharacterManagerView.vue` now fetches guild constants via `getGuildConstants()` API, filtering classes/specs/roles by guild's enabled expansions)*
  - [x] **Raids from DB based on enabled expansions:** guild's available raids are the union of `expansion_raids` for all enabled expansions. Raid definitions dynamically synced (created/soft-deleted) when expansions enabled/disabled.
  - [x] Class→role matrix defaults merge from the guild's enabled expansions
  - [x] Guild constants endpoint returns merged class/spec/role/raid data (`GET /api/v2/guilds/<id>/constants`)
- [x] **Realm customization (per-guild):** *(Done: all sub-items completed)*
  - [x] Guild owner can specify custom realm names for their guild (not hardcoded to Warmane realms)
  - [x] Create `GuildRealm` model — guild owner defines which realm(s) their guild plays on
  - [x] Different private servers have different realms — realm list is guild-configurable via `GuildRealm` model
  - [x] Character creation realm dropdown reads from guild's configured realms
  - [x] Remove hardcoded `WARMANE_REALMS` dependency from guild/character creation
  - [x] Warmane-specific realm list moves into Warmane plugin (Phase 5) as default/suggestion
- [ ] Create expansion selection flow in guild creation (guild admin picks highest expansion; cumulative auto-fill) *(Deferred: guild creation currently uses system defaults; expansion selection happens post-creation in guild settings. This is a UX enhancement for Phase 6 or later.)*
- [x] Update character creation to filter classes by guild's enabled expansions (from DB) *(Done: `CharacterManagerView.vue` loads guild-scoped constants via `getGuildConstants()` API, with fallback to system-wide expansion data)*
- [x] Update raid definition seeder for multi-expansion — dynamic sync on expansion enable/disable
- [x] Update frontend constants store to be fully expansion-aware *(Done: `src/stores/constants.js` fetches from backend `GET /api/v1/meta/constants` which returns expansion-aware data. Guild-scoped data available via `GET /api/v2/guilds/<id>/constants`. `useExpansionData` composable provides expansion store data.)*
- [x] Add expansion management in guild settings (guild owner/admin enables/disables)
- [x] **New admin permissions:**
  - [x] `manage_guild_expansions` — guild owner/admin: enable/disable expansion packs for guild
  - [x] `manage_guild_realms` — guild owner: configure guild's realm list
  - [x] `manage_expansions` — global admin: add/edit/disable expansion packs *(Done: added in Phase 1, `app/seeds/permissions.py` line 90, assigned to global_admin role, secures all v2 expansion admin endpoints)*
- [x] **Frontend co-migration:**
  - [x] Expansion management in guild settings (`GuildExpansionsTab.vue`)
  - [ ] Expansion selection in guild creation wizard (pick highest → auto-fill cumulative) *(Deferred: post-creation expansion selection in guild settings covers the use case. Wizard enhancement for Phase 6 or later.)*
  - [x] Realm configuration in guild settings (`GuildRealmsTab.vue`)
  - [x] Dynamic class/spec/role dropdowns merged across guild's enabled expansions *(Done: `CharacterManagerView.vue` fetches guild constants via `getGuildConstants()` API; guild constants endpoint returns merged class/spec/role data from enabled expansions)*
  - [x] Global admin expansion management UI *(Done: `ExpansionsTab.vue` in GlobalAdminView — full CRUD for expansions and raids, enable/disable, set default)*

> **⚡ Phase 4 → Phase 5 Interconnection (carried forward):**
> - ✅ All hardcoded realm lists removed. `WARMANE_REALMS` no longer exists anywhere in the codebase. Realms are fully dynamic — provided by armory providers via `fetch_realms()` API or managed manually per-guild via GuildRealmsTab.
> - ✅ `CharacterManagerView.vue`, `GuildSettingsTab.vue`, `GuildSettingsView.vue`, and `AppSidebar.vue` use guild-scoped realm API (`getGuildRealms()`) or `constantsStore.allRealms` (provider-based, dynamic).
> - ✅ Service-layer `ValueError` messages in `guild_service.py`, `tenant_service.py`, and `signup_service.py` migrated to `_t()` i18n keys (30+ strings, Phase 5).
> - Seed file deduplication: `_BASE_CLASS_SPECS` and `_BASE_SPEC_ROLE_MAP` in `app/seeds/expansions.py` are shared across Classic/TBC/WotLK. Future expansions (Cata+) may have different specs — extend via the global admin UI, not hardcoded dicts.
- [x] **🧹 Phase 4 cleanup** (see [§13.3.5](#1335-phase-4-cleanup-checklist)):
  - [x] Remove ALL remaining WotLK-only assumptions from frontend and backend
  - [x] Remove any `app/constants.py` re-exports that still exist (WARMANE_REALMS → Warmane plugin)
  - [x] Remove hardcoded WotLK class/raid lists from any component
  - [x] Remove hardcoded `WARMANE_REALMS` from `app/constants.py` → moved to plugin, re-export kept
  - [x] Verify `normalizeSpecName()` handles all expansion specs from DB
  - [x] Clean up dead expansion-related code paths
  - [x] Remove `WowClass` Python enum from `app/enums.py` — all class validation is now DB-driven *(Done: `Character.class_name` changed to `sa.String(50)`)*
  - [x] Run full lint + build + test suite on clean branch *(823 tests pass, frontend builds)*

> **📊 Phase 4 Completion Summary (823 tests, frontend builds):**
> - Multi-expansion support: guilds can enable/disable expansions; classes/specs/roles/raids merge from enabled expansions
> - Character creation uses guild-scoped expansion data via `getGuildConstants()` API
> - Realm customization: per-guild via `GuildRealm` model + `GuildRealmsTab.vue`; all hardcoded realm lists removed
> - Global admin: full CRUD for expansions and raids in `ExpansionsTab.vue`
> - All WotLK-only assumptions removed: no `WOW_CLASSES`, `RAID_TYPES`, `WARMANE_REALMS` anywhere
> - `WowClass` enum removed — `Character.class_name` uses `sa.String(50)`, validation is DB-driven
> - Deferred items (non-blocking): expansion selection in guild creation wizard, JSON/CSV import, admin class/spec CRUD

### Phase 5: Plugin Architecture
**Goal:** Make features truly pluggable.

> **⚡ Cross-Phase Dependencies & Interconnections:**
> - **Phase 5 ← Phase 1:** Expansion packs become plugins that populate the expansion registry tables.
> - **Phase 5 ← Phase 4:** Per-guild expansion settings and realm configuration are managed through plugin interfaces.
> - **Phase 5 completes:** Armory integration is wrapped in a generic, server-agnostic armory plugin. Realms are fully dynamic — no hardcoded lists anywhere. Guild member addition via armory is a plugin feature, not a default. The default flow is invitation-based (Phase 0/2).

- [x] Create `app/plugins/` framework (BasePlugin, PluginRegistry)
- [x] Create generic **armory plugin** (`app/plugins/armory/`) — server-agnostic, not tied to any specific server
- [x] Refactor Discord integration into a plugin (`app/plugins/discord/`)
- [x] Create v2 plugin API:
  - [x] `GET /api/v2/plugins/` — list all plugins
  - [x] `GET /api/v2/plugins/<key>` — get plugin metadata
  - [x] `GET /api/v2/plugins/<key>/config` — get plugin config
  - [x] `GET /api/v2/plugins/armory/providers` — list armory providers
  - [x] `GET /api/v2/plugins/armory/providers/<name>/realms` — get provider realm suggestions (dynamic from API)
- [x] Build plugin management UI (PluginsTab in GlobalAdminView)
- [x] Frontend plugin store (`src/plugins/registry.js`) and API client (`src/api/plugins.js`)
- [x] **Remove all hardcoded realm lists:**
  - [x] Remove `WARMANE_REALMS` from `app/constants.py` entirely
  - [x] Remove `WARMANE_REALMS` from `src/constants.js` entirely
  - [x] Remove `warmaneRealms` from constants store → replaced with `providerRealms` + `allRealms`
  - [x] Remove `warmane_realms` from meta API → replaced with `provider_realms` (dynamic from providers)
  - [x] Remove `DEFAULT_REALMS` from `WarmaneProvider` — zero hardcoded realm data
  - [x] Remove realm seeding on guild creation — guilds manage realms manually via GuildRealmsTab
- [x] **Dynamic realm architecture:**
  - [x] `ArmoryProvider.fetch_realms()` — providers can discover realms from their API
  - [x] `ArmoryProvider.get_default_realms()` — returns `[]` by default
  - [x] `ArmoryPlugin.get_provider_realms()` — tries `fetch_realms()` then `get_default_realms()`
  - [x] Guilds manage their own realms via `GuildRealm` model + GuildRealmsTab UI
- [x] Migrate all service-layer hardcoded English strings to `_t()` i18n (guild_service, tenant_service, signup_service — 30+ strings)
- [x] Add 60+ i18n keys (plugin, guild.errors, tenant.errors, signup.errors) in en.json + pl.json
- [x] 25 plugin tests (ArmoryPlugin, PluginRegistry, v2 API, provider tests) — now 27 tests
- [ ] Create plugin developer documentation *(Deferred: plugin architecture is stable but documentation is a Phase 6+ deliverable)*
- [x] **New admin permissions:**
  - [x] `manage_plugins` — global admin: enable/disable system plugins (added to seeds/permissions.py and assigned to global_admin role; plugin config endpoint protected)
- [x] **🧹 Phase 5 cleanup** (see [§13.3.6](#1336-phase-5-cleanup-checklist)):
  - [x] Remove all hardcoded realm lists (WARMANE_REALMS → zero references in codebase)
  - [ ] Remove inline Warmane API calls from services — all go through plugin interface *(Deferred: existing armory provider system already provides sufficient abstraction; warmane.py is a provider, not a direct integration)*
  - [ ] Remove inline Discord integration from services — all go through plugin interface *(Deferred: Discord OAuth is auth-layer, not guild-level plugin concern)*
  - [x] Run full lint + build + test suite on clean branch (823 tests pass, frontend builds)

> **📊 Phase 5 Completion Summary (823 tests, frontend builds):**
> - Plugin framework: `BasePlugin`/`PluginRegistry` in `app/plugins/base.py`
> - Plugins implemented: `ArmoryPlugin` (server-agnostic), `DiscordPlugin` (metadata wrapper)
> - Plugin API: `GET /api/v2/plugins/`, `GET /api/v2/plugins/<key>`, `GET /api/v2/plugins/<key>/config`, armory provider endpoints
> - Plugin admin UI: `PluginsTab.vue` in GlobalAdminView
> - Dynamic realms: `ArmoryProvider.fetch_realms()` replaces all hardcoded realm lists. Zero `WARMANE_REALMS` references anywhere.
> - i18n: 30+ service-layer ValueError strings migrated to `_t()`. 60+ i18n keys added.
> - Security: `manage_plugins` permission added, plugin config endpoint secured with `require_system_permission()`
> - 27 plugin tests. CodeQL clean.
> - Deferred items (non-blocking): plugin developer documentation, inline Warmane/Discord service refactoring

### Phase 6: SaaS Infrastructure
**Goal:** Add billing, plan management, and tenant management from the global
admin panel.

> **Decision §9.4 #1:** Global admin must be able to create and configure
> subscription plans (one free plan, multiple paid plans with different limits).
> Global admin can assign plans to specific tenants.

> **⚡ Cross-Phase Dependencies & Interconnections:**
> - **Phase 6 ← Phase 0:** Tenant model is the billing unit. `max_guilds`/`max_members` fields on Tenant (Phase 0) become plan-driven.
> - **Phase 6 ← Phase 5:** Plugin system provides the feature toggle mechanism for plan-based feature gating.
> - **Phase 6 completes:** v1 API deprecation review — assess if v1 endpoints can be fully removed.

- [x] ~~Evaluate need for row-level tenancy (tenant_id enforcement)~~ → **Moved to Phase 0**
- [ ] Create `Plan` model (name, slug, limits, features, is_free, price_info)
- [ ] Seed default free plan with configurable limits
- [ ] Global admin UI for plan management:
  - [ ] Create/edit/delete plans
  - [ ] Configure plan limits (guilds, members, events, features)
  - [ ] Mark one plan as the free/default plan
  - [ ] Create multiple paid plans with different feature sets
  - [ ] Assign plans to specific tenants (override default)
- [ ] Add subscription/billing model per tenant (free / pro / enterprise plans)
- [ ] Add usage tracking per tenant (guilds, members, events)
- [ ] Add API rate limiting per tenant (based on plan)
- [ ] Add data export/import for tenant portability
- [ ] Add tenant deletion with full data cleanup
- [ ] Add tenant suspension/reactivation by global admin
- [ ] **New admin permissions:**
  - [ ] `manage_plans` — global admin: create/edit/delete subscription plans
  - [ ] `manage_billing` — global admin: view/manage tenant billing
- [ ] **Frontend co-migration:**
  - [ ] Plan management UI in global admin panel
  - [ ] Tenant plan assignment UI
  - [ ] Plan usage dashboard for tenant owners
  - [ ] Plan limits enforcement in frontend (show upgrade prompts)
- [ ] **🧹 Phase 6 cleanup** (see [§13.3.7](#1337-phase-6-cleanup-checklist)):
  - [ ] Remove free-plan hardcoded defaults if plan limits now come from billing model
  - [ ] Remove any manual guild/member counting if usage tracking replaces it
  - [ ] Clean up Phase 0 `max_guilds`/`max_members` defaults if billing system overrides them
  - [ ] Final full-codebase dead-code audit (see §13.4)
  - [ ] **v1 API deprecation review:** Assess if v1 endpoints can now be fully removed or if they need to remain for any legacy integrations
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

- **v1 stays intact as backup** — the existing `/api/v1/` endpoints remain
  functional and unchanged even on the migration branch. This provides a
  rollback path and avoids breaking any existing integrations.
- **v2 for all new work** — all new multi-tenant endpoints, tenant-scoped
  routes, and refactored endpoints use `/api/v2/` prefix. Both v1 and v2
  coexist during migration.
- **v1 deprecation** — once all v2 endpoints are stable, tested, and the
  frontend has fully migrated to v2, the v1 blueprints can be deprecated
  and eventually removed in a future cleanup phase.
- **Blueprint structure:** `app/api/v2/` mirrors `app/api/v1/` structure
  but with tenant-aware routes. v2 blueprints register under `/api/v2/`
  prefix.

### 8.3 Frontend Compatibility

- Constants store should gracefully handle missing expansion data
- Components should use optional chaining for new fields
- New UI features should be behind feature flag checks

### 8.4 CodeQL Policy

- CodeQL scans must ONLY be run at the **end of all changes** for a phase, never during intermediate agent work
- After the final scan, fix all findings before marking the phase complete
- This avoids wasting CI/agent resources on scans during active development

### 8.5 Shared Utilities & Code Reuse Policy

- **Always** use existing helpers, decorators, and shared utilities:
  - Backend: `_t()` (i18n), `validate_required()`, `get_json()`, `get_event_or_404()`, `has_permission()`, `require_system_permission()`, `@login_required`, `@require_guild_permission()`
  - Backend spec/role: `allowed_roles_for_class()`, `allowed_specs_for_class()`, `validate_class_role()`, `validate_class_spec()`, `normalize_spec_name()` — all from `app/utils/class_roles.py`
  - Frontend: composables (`usePermissions`, `useSocket`, `useWowIcons`, `useExpansionData`), store patterns, API helpers
- **Never** duplicate code — if new shared logic is needed, create a helper, decorator, utility, or composable
  - **Specifically:** never create local `_require_permission()` or `_require_admin()` in API files — always use `require_system_permission()` from `app/utils/api_helpers.py`
- New API endpoints must follow established patterns (error responses via `_t()`, validation via `validate_required()`, permission checks via `require_system_permission()`)
- `jsonify` must not be used with hardcoded English strings — always use `_t()` translation keys

---

## 9. Open Questions & Decisions

### 9.1 Resolved Decisions

All questions have been decided. These are the **final answers** that inform
all subsequent phases.

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Where to store expansion definitions? | **Database tables** | Expansions will be pluggable from the global admin panel. Hardcoding classes/roles in Python dicts or enums makes no sense in a multi-tenant system with pluggable expansions — every new expansion would require code changes and redeployment. DB-driven definitions allow global admins to add/configure expansions at runtime. |
| 2 | Should guilds support multiple expansions simultaneously? | **Yes — per-guild, cumulative expansions** | Expansion configuration is **per-guild** because a single tenant can have guilds from different servers (e.g., a WotLK guild and a TBC guild). The **guild owner/admin** enables which expansion packs their guild uses. **Expansions are cumulative:** enabling a later expansion (e.g., WotLK) automatically includes all previous expansions (Classic, TBC), because each expansion contains all content from prior versions. |
| 3 | How to handle spec changes across expansions? | **DB-driven, pluggable** | When a new expansion is added to the system (by global admin), its classes, specs, and roles are loaded from the expansion's DB records. No hardcoded enum — the system reads from `expansion_classes`, `expansion_specs`, `expansion_roles` tables. API endpoint returns the data for the guild's active expansion. |
| 4 | Should class-role matrix overrides be per-raid or per-guild? | **Per-guild** with pluggable expansions | Guild admins configure the class→role matrix for their guild. The matrix defaults come from the guild's enabled expansion packs (merged), and guild admins can customize. Per-raid overrides may be added as a future extension. |
| 5 | Invitation expiry default? | **Guild admin configurable, max 30 days** | Guild admins select the expiry duration when creating an invitation. The system enforces a maximum expiration of 30 days — no invitation can live longer than that. |
| 6 | Allow users to see guilds they're not members of? | **Configurable per guild** within the tenant (visibility setting) | Hidden guilds are NOT shown in the sidebar navigation. They are only visible on a dedicated **guild discovery/browser page** within the tenant (added in Phase 2). Open guilds appear in both sidebar and discovery page. |
| 7 | Database name change from `wotlk_calendar.db`? | **Yes** — rename to `raid_calendar.db` | Done in Phase 0 as part of tenant migration. |
| 8 | Should the `WowClass` Python enum remain? | **No** — replace with **expansion-dynamic DB-driven** approach | Hardcoding all classes as a Python enum makes no sense when expansions are pluggable. Classes come from the DB expansion tables. The `WowClass` enum will be removed once DB-driven class definitions are in place (Phase 1/4). |
| 9 | Should the default expansion be a named constant? | **DB-driven** — default expansion should be a system setting returned by a proper API endpoint, because expansions are pluggable | No hardcoded `DEFAULT_EXPANSION` constant. The global admin configures which expansion is the default via the admin panel, stored in `system_settings` table, and returned by `GET /api/v2/meta/default-expansion`. |
| 10 | Default guild limit per tenant? | **3** (configurable by global admin, with ability to override per-tenant) | Global admin can change the system-wide default and also override for specific tenants. |
| 11 | Default member limit per tenant? | **Unlimited** for now (configurable from global admin panel) | No artificial member cap initially. Global admin can set/change limits per plan or per tenant. |
| 12 | Should tenant invitations be shareable (multi-use) by default? | **Configurable** with expiry, max 30 days | Invitations can be single-use or multi-use. All invitations expire — max allowed expiry is 30 days. |
| 13 | How should tenant slug be generated? | **Randomly generated**, customizable in guild admin panel | Auto-generated random slug at creation; guild admins can customize it later from the admin panel. |

### 9.2 Research Items

- [ ] Survey private server APIs (TrinityCore, AzerothCore, CMaNGOS) for armory integration possibilities
- [ ] Investigate retail WoW Blizzard API for character/guild data access
- [ ] Evaluate whether Monk/DH/Evoker specs need additional Role enum values (e.g., "support" for Augmentation Evoker)
- [ ] Research demand for non-WoW game support (FFXIV, ESO) — affects how generic the plugin system should be

### 9.3 Technical Debt to Address First

Before starting Phase 1, complete these from the existing cleanup plan:
- [x] Consolidate frontend role label maps (7 duplicates) — resolved: components use `useExpansionData()` composable
- [x] Consolidate CLASS_ROLES/CLASS_SPECS between frontend and backend — resolved: removed from both, now DB-driven
- [ ] Add service layers for modules that access DB directly (raid_definitions, templates, series, roles)

> **Current status (post-Phase 1):**
> - All expansion data (classes, specs, roles, raids) is DB-driven — no hardcoded enums used for validation
> - `normalize_spec_name()` moved to `app/utils/class_roles.py` (DB-driven, expansion-pluggable)
> - `require_system_permission()` extracted to shared `app/utils/api_helpers.py`
> - Frontend uses shared utilities (`WowCard`, `WowButton`, `WowModal`, `InviteLinkCard`, etc.) — no inline styling or code duplication
> - Guild membership is invitation-based (not armory-based) in multi-tenant model
> - Invite accept requires login/register first (router guard redirects with redirect param)

### 9.4 Additional Requirements (Future Implementation Points)

These requirements were identified during decision review and must be
incorporated into the appropriate phases:

| # | Requirement | Affects Phase(s) | Details |
|---|-------------|-----------------|---------|
| 1 | **Global admin: paid/free plan configuration** | Phase 6 | Global admin must be able to create and configure subscription plans (one free plan, multiple paid plans). Plans define limits (guilds, members, features). Global admin can assign plans to tenants. |
| 2 | **DB-driven classes/roles/specs** (no hardcoded enums) | Phase 1, 3, 4 | Hardcoding all classes and roles will not work in a multi-tenant system with pluggable expansions. Every class, role, and spec must come from DB tables tied to expansion packs. The `WowClass` enum and `CLASS_ROLES`/`CLASS_SPECS` dicts must be replaced with DB-driven definitions. |
| 3 | **v1 API preserved as backup; v2 for all new work** | Phase 0+ | Keep the existing `/api/v1/` endpoints intact as a fallback even on the migration branch. All new multi-tenant endpoints use `/api/v2/` prefix. This provides a rollback path and avoids breaking any existing integrations during migration. |
| 4 | **Frontend + backend co-migration per phase** | All phases | Frontend and backend changes for each phase must happen simultaneously in the same branch/PR. No phase should ship backend changes without the matching frontend changes — this prevents drift and integration bugs. |
| 5 | **Admin permissions and references** | Phase 0+ | Each phase must define and document the new admin permissions it introduces, add them to the permission seed, and reference them in the phase checklist. No implicit permissions. |
| 6 | **Bench/queue system multi-tenant isolation** | Phase 0 | The bench/queue system is a critical concern. Each tenant must have its own isolated job queue, bench queue, and auto-promotion logic. The current `JobQueue` table and `process_job_queue()` scheduler must be tenant-aware. Auto-lock, auto-promote, and character sync jobs must all be scoped by `tenant_id`. See §10.21 for detailed plan. |

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
    Auto-created when a user registers. The owner has full control.
    Each tenant has a customizable name and description."""

    __tablename__ = "tenants"

    id            = Column(Integer, primary_key=True)
    name          = Column(String(100), nullable=False)
    description   = Column(Text, nullable=True)              # Tenant description (shown in UI)
    slug          = Column(String(100), unique=True, nullable=False)
    owner_id      = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    plan          = Column(String(30), default="free")      # free / pro / enterprise
    max_guilds    = Column(Integer, default=3)               # guild limit per plan
    max_members   = Column(Integer, nullable=True)           # member limit (NULL = unlimited)
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

> **Note:** Per §8.2 and §9.4 #3, all new tenant-aware endpoints use `/api/v2/`
> prefix. The existing `/api/v1/` endpoints remain unchanged as backup. The v2
> routes below mirror the v1 structure but with tenant-scoped logic.

#### 10.9.1 New Tenant Routes

```python
# app/api/v2/tenants.py (NEW BLUEPRINT — under /api/v2/)

# Tenant CRUD (for tenant owners):
GET    /api/v2/tenants                           # List user's tenants (owned + member)
GET    /api/v2/tenants/<int:tenant_id>            # Get tenant details
PUT    /api/v2/tenants/<int:tenant_id>            # Update tenant settings
DELETE /api/v2/tenants/<int:tenant_id>            # Delete tenant (owner only)

# Tenant members:
GET    /api/v2/tenants/<int:tenant_id>/members                    # List members
POST   /api/v2/tenants/<int:tenant_id>/members                    # Add member directly
PUT    /api/v2/tenants/<int:tenant_id>/members/<int:user_id>      # Update member role
DELETE /api/v2/tenants/<int:tenant_id>/members/<int:user_id>      # Remove member

# Tenant invitations (max expiry: 30 days):
GET    /api/v2/tenants/<int:tenant_id>/invitations                # List invitations
POST   /api/v2/tenants/<int:tenant_id>/invitations                # Create invite (link/discord/direct)
DELETE /api/v2/tenants/<int:tenant_id>/invitations/<int:inv_id>   # Revoke invitation
POST   /api/v2/invite/<token>                                     # Accept invite (public endpoint)

# Tenant switching:
PUT    /api/v2/auth/active-tenant                                 # Switch active tenant
GET    /api/v2/auth/active-tenant                                 # Get current active tenant
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
# app/api/v2/admin.py — New endpoints (under /api/v2/):

GET    /api/v2/admin/tenants                                      # List all tenants (with stats)
GET    /api/v2/admin/tenants/<int:tenant_id>                      # Get tenant details
PUT    /api/v2/admin/tenants/<int:tenant_id>                      # Update tenant (limits, plan)
POST   /api/v2/admin/tenants/<int:tenant_id>/suspend              # Suspend tenant
POST   /api/v2/admin/tenants/<int:tenant_id>/activate             # Reactivate tenant
DELETE /api/v2/admin/tenants/<int:tenant_id>                      # Delete tenant + all data
PUT    /api/v2/admin/tenants/<int:tenant_id>/limits               # Override guild/member limits
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
2. Frontend calls `PUT /api/v2/auth/active-tenant` with new `tenant_id`
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
| `get_json()` | ✅ Stable | Extract JSON body from request |
| `validate_required()` | ✅ Stable | Check required fields present in data dict |
| `require_system_permission()` | ✅ **New (Phase 1)** | System-level permission check — replaces duplicated `_require_permission()` / `_require_admin()` in admin.py, meta.py, admin_tenants.py |
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
- [ ] **Step 0.16:** Create tenant API blueprint (`app/api/v2/tenants.py`)
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
| **New files** | `app/models/tenant.py`, `app/models/mixins.py`, `app/api/v2/tenants.py`, `src/components/admin/TenantsTab.vue`, `src/components/sidebar/TenantSwitcher.vue` | 5 new files |
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
| 13 | **v1 API preserved; v2 for new work** | Keep existing v1 endpoints unchanged as backup/rollback path. All new tenant-aware endpoints use `/api/v2/` prefix. Frontend migrates to v2. v1 deprecated in Phase 6. |
| 14 | **Frontend + backend co-migration** | No phase ships backend changes without matching frontend. Both sides migrate simultaneously to prevent drift and integration bugs. |
| 15 | **DB-driven expansion data** (not Python dicts/enums) | Hardcoded classes/roles/specs cannot work with pluggable expansions. All expansion data comes from DB tables. Global admin adds expansions at runtime without code changes. |
| 16 | **Tenant member limit: unlimited** (default) | No artificial member cap initially. Global admin configures limits per-plan or per-tenant as needed. |
| 17 | **Invitation max expiry: 30 days** | No invitation lives longer than 30 days. Guild admin selects duration within this limit. |
| 18 | **Tenant slug: random, customizable** | Auto-generated random slug at creation. Customizable from admin panel later. |
| 19 | **Database renamed to `raid_calendar.db`** | Old name `wotlk_calendar.db` implies single-expansion. Renamed in Phase 0. |
| 20 | **Tenant has name + description** | Each tenant has a customizable `name` (required) and `description` (optional). Displayed in UI (sidebar, invite page, settings). Owner/admin can update. |
| 21 | **Notification `tenant_id` auto-derived from guild** | `_notify()` helper auto-derives `tenant_id` from `guild_id` — no need to change 20+ call sites. System-wide notifications keep `tenant_id=NULL`. |
| 22 | **Socket.IO: add `tenant_{id}` room, keep guild/event rooms unchanged** | Guild rooms are implicitly tenant-scoped (guild belongs to tenant). Only tenant-level events (invite, member join) need a dedicated `tenant_{id}` room. |

### 10.21 Bench/Queue System — Multi-Tenant Isolation

> **Concern:** The bench/queue system is one of the most complex parts of the
> application. It involves background jobs (APScheduler), the `JobQueue` table,
> bench queue ordering (`LineupSlot` with `slot_group="bench"`), auto-promotion
> logic, and auto-lock scheduling. Each of these must be tenant-aware.

#### 10.21.1 Current Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ APScheduler (BackgroundScheduler)                                │
│   ├── process_job_queue()  — polls JobQueue table every 30s      │
│   ├── auto_lock_upcoming_events() — locks events every 5 min     │
│   └── autosync_characters() — syncs armory data (configurable)   │
│                                                                  │
│ JobQueue table (in-DB queue)                                     │
│   ├── type: "send_notification" / "sync_all_characters"          │
│   ├── payload: JSON dict with context (user_id, guild_id, etc.)  │
│   ├── status: queued / running / done / failed                   │
│   └── NO tenant_id today — global queue                          │
│                                                                  │
│ Bench Queue (LineupSlots with slot_group="bench")                │
│   ├── Ordered by slot_index within a raid event                  │
│   ├── auto_promote_bench() — promotes bench → lineup on cancel   │
│   └── Scoped by raid_event_id (which is guild-scoped)            │
└──────────────────────────────────────────────────────────────────┘
```

#### 10.21.2 Multi-Tenant Changes

**JobQueue table:**

| Change | Details |
|--------|---------|
| Add `tenant_id` column | FK to `tenants.id`, NOT NULL for tenant-scoped jobs. Nullable for system-wide jobs (e.g., global maintenance). |
| Add `guild_id` column | FK to `guilds.id`, nullable. For guild-scoped jobs (character sync, notifications). |
| Index `(tenant_id, status)` | Efficient polling per-tenant. |

**`process_job_queue()` changes:**

```python
# Current: claims ANY queued job globally
# After: still processes all tenants, but adds tenant_id to context

def process_job_queue(app: Flask) -> None:
    """Drain queued jobs — processes all tenants fairly."""
    with app.app_context():
        # Jobs are processed in order regardless of tenant (FIFO).
        # tenant_id is included in the job payload for handler context.
        # Each handler must scope its operations by tenant_id.
        ...
```

> **Design decision:** The job queue processor does NOT run per-tenant
> schedulers. A single scheduler processes all jobs in FIFO order. The
> `tenant_id` on each job ensures handlers scope their operations correctly.
> This is simpler than running N schedulers and avoids resource issues.

**`auto_lock_upcoming_events()` changes:**

```python
# Current:
RaidEvent.status == "open"

# After: add tenant scope via guild → tenant join
sa.select(RaidEvent)
  .join(Guild, RaidEvent.guild_id == Guild.id)
  .where(
    RaidEvent.status == "open",
    Guild.tenant_id.isnot(None),  # Only process tenant-scoped events
    ...
  )
```

This is already implicitly tenant-scoped (events belong to guilds, guilds
belong to tenants), but the explicit join ensures no orphaned events from
deleted tenants are processed.

**`handle_sync_all_characters()` changes:**

```python
# Current: syncs ALL active characters globally
# After: scope by tenant_id from job payload

guild_id = payload.get("guild_id")
tenant_id = payload.get("tenant_id")

stmt = sa.select(Character).where(Character.is_active.is_(True))
if tenant_id:
    stmt = stmt.join(Guild, Character.guild_id == Guild.id) \
               .where(Guild.tenant_id == tenant_id)
if guild_id:
    stmt = stmt.where(Character.guild_id == guild_id)
```

**Bench queue (`auto_promote_bench()`) changes:**

The bench queue is already scoped by `raid_event_id`, which belongs to a
guild, which belongs to a tenant. No direct changes needed to the bench
promotion logic itself. However:

- [ ] Verify `_auto_promote_bench()` never queries LineupSlots without
  a `raid_event_id` filter (preventing cross-event/cross-guild leaks)
- [ ] Verify `get_bench_info()` in `lineup_service.py` is scoped correctly
- [ ] Verify `reorder_bench()` in `lineup_service.py` is scoped correctly
- [ ] Add integration tests that create bench queues in two different
  tenants and verify no cross-tenant data leaks in promotion

**Autosync schedule — per-tenant:**

Currently autosync is a global setting (`SystemSetting` table). With
multi-tenancy, autosync could be:
- **Option A:** Global setting only — platform admin controls sync schedule.
  All tenants' characters sync on the same schedule.
- **Option B:** Per-tenant setting — each tenant owner can configure their
  own sync interval (within platform limits).

**Recommendation:** Start with **Option A** (global) in Phase 0. Evaluate
per-tenant sync in Phase 5 (plugin architecture) if needed.

#### 10.21.3 Verification

```bash
# Verify JobQueue has tenant_id
grep -rn "tenant_id" app/models/notification.py  # JobQueue model

# Verify handlers scope by tenant_id
grep -rn "tenant_id" app/jobs/handlers.py

# Verify bench queue isolation
grep -rn "tenant_id\|guild_id" app/services/lineup_service.py | grep -i "bench\|queue"

# Integration tests
python -m pytest tests/test_bench_tenant_isolation.py -v
```

### 10.22 Notification System — Multi-Tenant Isolation

> **Concern:** The notification system is deeply woven through the application —
> `notify.py` has 20+ helper functions, Socket.IO pushes in real-time, and
> notifications can be guild-scoped or system-wide. With multi-tenancy, we need
> to ensure: (a) tenant-scoped notifications don't leak across tenants, (b)
> system-wide notifications still reach all users, (c) Socket.IO rooms are
> tenant-aware, and (d) the notification list can be filtered by tenant.

#### 10.22.1 Current Notification Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Notification Creation Flow:                                      │
│   notify.py helpers (20+ functions)                              │
│     → notification_service.create_notification()                 │
│     → Notification row in DB                                     │
│     → socketio.emit("notification", {}, to=f"user_{user_id}")    │
│                                                                  │
│ Notification Model:                                              │
│   user_id (required) — who receives it                           │
│   guild_id (nullable) — which guild context                      │
│   raid_event_id (nullable) — which event context                 │
│   type — one of 20+ types (signup_confirmed, event_created, etc) │
│   title, body — pre-rendered English text                        │
│   title_key, body_key, *_params — i18n translation keys          │
│   NO tenant_id today                                             │
│                                                                  │
│ Socket.IO Rooms:                                                 │
│   user_{user_id} — per-user notification room                    │
│   event_{event_id} — per-event realtime updates                  │
│   guild_{guild_id} — per-guild realtime updates                  │
│   NO tenant-level rooms today                                    │
│                                                                  │
│ Notification Types (20+):                                        │
│   signup_* — signup lifecycle (confirmed, benched, promoted, etc) │
│   event_* — event lifecycle (created, updated, cancelled, etc)   │
│   guild_* — guild membership (joined, removed, role_changed)     │
│   officer_* — officer alerts (new signup, bench changed, etc)    │
│   NO tenant-level types today                                    │
└──────────────────────────────────────────────────────────────────┘
```

#### 10.22.2 Multi-Tenant Changes

**Notification model:**

| Change | Details |
|--------|---------|
| Add `tenant_id` column | FK to `tenants.id`, **nullable**. Nullable because some notifications are system-wide (password change, account alerts). Guild-scoped notifications always have `tenant_id` set (derived from guild's tenant). |
| Add index `(tenant_id, user_id, read_at)` | Efficient per-tenant notification queries with read/unread filtering. |

**`notification_service.py` changes:**

```python
# create_notification() — add tenant_id parameter:
def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    guild_id: Optional[int] = None,
    raid_event_id: Optional[int] = None,
    tenant_id: Optional[int] = None,          # NEW
    *,
    title_key: Optional[str] = None,
    ...
) -> Notification:
    ...

# list_notifications() — add optional tenant_id filter:
def list_notifications(
    user_id: int,
    *,
    tenant_id: Optional[int] = None,          # NEW: filter by tenant
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    stmt = sa.select(Notification).where(Notification.user_id == user_id)
    if tenant_id is not None:
        # Show notifications for this specific tenant + system-wide (tenant_id=NULL)
        stmt = stmt.where(
            sa.or_(
                Notification.tenant_id == tenant_id,
                Notification.tenant_id.is_(None),
            )
        )
    ...

# unread_count() — add optional tenant_id filter:
def unread_count(user_id: int, *, tenant_id: Optional[int] = None) -> int:
    stmt = sa.select(sa.func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    )
    if tenant_id is not None:
        stmt = stmt.where(
            sa.or_(
                Notification.tenant_id == tenant_id,
                Notification.tenant_id.is_(None),
            )
        )
    ...
```

**`notify.py` helpers — all 20+ functions:**

Every notification-creating function in `notify.py` already receives `guild_id`.
The `tenant_id` can be derived from the guild:

```python
def _notify(
    user_id: int,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    guild_id: Optional[int] = None,
    raid_event_id: Optional[int] = None,
    tenant_id: Optional[int] = None,          # NEW
    *,
    ...
) -> None:
    # Auto-derive tenant_id from guild if not provided:
    if tenant_id is None and guild_id is not None:
        guild = db.session.get(Guild, guild_id)
        if guild:
            tenant_id = guild.tenant_id

    create_notification(
        ...,
        tenant_id=tenant_id,
    )
```

> **Design decision:** We do NOT need to change every call site in `notify.py`.
> Instead, the `_notify()` internal helper auto-derives `tenant_id` from
> `guild_id`. This means all 20+ notification functions get tenant context
> automatically without modification. Only system-wide notifications (no guild)
> will have `tenant_id=NULL`, which is correct.

**New notification types for tenant events:**

| Type | When | Context |
|------|------|---------|
| `tenant_invite_received` | User receives a tenant invitation | `tenant_id` set, no `guild_id` |
| `tenant_member_joined` | New member accepts invitation and joins tenant | Sent to tenant admins; `tenant_id` set |
| `tenant_member_removed` | Member is removed from tenant | Sent to the removed user; `tenant_id` set |
| `tenant_settings_changed` | Tenant settings updated (name, description, etc.) | Sent to tenant members; `tenant_id` set |

**Notifications API (`notifications.py`) changes:**

```python
# v2 list endpoint supports tenant_id query param:
@bp.get("")
@login_required
def list_notifications():
    tenant_id = request.args.get("tenant_id", type=int)
    # If tenant_id provided, validate user is a member of that tenant
    if tenant_id:
        # Verify membership...
        pass
    notifications = notification_service.list_notifications(
        current_user.id, tenant_id=tenant_id, limit=limit, offset=offset
    )
    ...

# v2 unread-count endpoint supports tenant_id query param:
@bp.get("/unread-count")
@login_required
def unread_count():
    tenant_id = request.args.get("tenant_id", type=int)
    count = notification_service.unread_count(
        current_user.id, tenant_id=tenant_id
    )
    ...
```

**Socket.IO room changes:**

```
CURRENT ROOMS:
  user_{user_id}        — per-user notifications
  event_{event_id}      — per-event updates
  guild_{guild_id}      — per-guild updates

AFTER TENANCY:
  user_{user_id}        — KEEP: system-wide notifications (password, account)
  tenant_{tenant_id}    — NEW: tenant-level events (member joined, settings changed)
  guild_{guild_id}      — KEEP: guild-level updates (unchanged — guilds are tenant-scoped)
  event_{event_id}      — KEEP: event-level updates (unchanged — events are guild-scoped)
```

> **Design decision:** We do NOT prefix guild/event rooms with `tenant_id`.
> Guilds already belong to a tenant, so `guild_{guild_id}` is implicitly
> tenant-scoped (a user can only join a guild room if they're a member of
> that guild's tenant). Adding a `tenant_{tenant_id}` room is only needed
> for tenant-level events (invite, member changes, settings).

**Frontend changes (see also §11):**

| Component | Change |
|-----------|--------|
| `useSocket` composable | Join `tenant_{activeTenantId}` room on connect; leave old tenant room on tenant switch |
| Notification bell/dropdown | Pass `tenant_id` query param to filter notifications by active tenant |
| Unread count badge | Pass `tenant_id` to unread-count endpoint for per-tenant count |
| Notification panel | Show tenant name context for each notification (e.g., "[TenantName] Signup confirmed") |
| Tenant settings page | Show notifications when tenant settings (name, description) are changed |

#### 10.22.3 Notification Scoping Rules

| Notification Category | `tenant_id` | Visible When |
|-----------------------|-------------|--------------|
| **Guild-scoped** (signup, event, lineup, officer) | Set (from guild's tenant) | User is in the matching tenant context, or viewing "all tenants" |
| **Tenant-scoped** (invite, member joined, settings changed) | Set | User is in the matching tenant context, or viewing "all tenants" |
| **System-wide** (password changed, account alerts) | NULL | Always visible, regardless of active tenant |

**Query behavior:**
- **Default (no filter):** Show all notifications for the user across all tenants + system-wide
- **With `tenant_id` filter:** Show notifications matching that `tenant_id` + system-wide (`tenant_id IS NULL`)
- **"All tenants" view:** Same as default — show everything

#### 10.22.4 Verification

```bash
# Verify Notification model has tenant_id
grep -rn "tenant_id" app/models/notification.py | grep -i "notif"

# Verify notify.py passes tenant_id
grep -rn "tenant_id" app/utils/notify.py

# Verify notification service supports tenant_id filter
grep -rn "tenant_id" app/services/notification_service.py

# Verify Socket.IO tenant room
grep -rn "tenant_" app/utils/realtime.py

# Integration tests
python -m pytest tests/test_notification_tenant_isolation.py -v
```

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
            → constants store (expansion data from DB via /api/v2/meta/*)

All API calls migrate from /api/v1/* to /api/v2/* (v1 stays as backup).

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
> (session/cookie). The `X-Tenant-Id` header is an **additional safety check**:
> on every request the backend **validates** that the header value matches
> `user.active_tenant_id` and **rejects with 409 Conflict** if they differ.
> This prevents a stale browser tab (that missed a tenant switch in another
> tab) from accidentally writing data to the wrong tenant.

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
  ID | Name | Description | Owner | Plan | Guilds (used/max) | Members (used/max) | Status | Actions
- Actions per tenant:
  - View Details → modal with tenant info (name, description) + member list
  - Edit → modal to change name, description, max_guilds, max_members, plan
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
- Fetches invite details by token: GET /api/v2/invite/{token}/details
- Shows: tenant name, tenant description, inviter name, role being assigned, expiry
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

| File | Reason | Status |
|------|--------|--------|
| `src/components/admin/SystemTab.vue` | Orphaned; never imported. Functionality lives in `UsersTab.vue` + `SettingsTab.vue`. | ✅ Deleted |

**Code to remove/refactor:**

| Location | What | Action | Status |
|----------|------|--------|--------|
| `AppSidebar.vue` lines 33-50 | "Available guilds to join" section | **Remove** — guild discovery is now within tenant context; users join tenants first, then guilds within | ✅ Done |
| `AppSidebar.vue` `availableGuilds` computed | Computed property filtering `allGuilds` by `allow_self_join` | **Remove** — replaced by tenant invitation system | ✅ Done |
| `guild_service.py` `list_all_guilds()` | Lists ALL guilds in the system (no tenant filter) | **Refactor** — must filter by `tenant_id`; old global listing is a security risk | ✅ Done |
| `guilds.py` API `GET /guilds/all` | Returns all guilds without tenant scoping | **Refactor** — scope to active tenant; global admin has separate endpoint | ✅ Done |
| `guild_service.py` `create_guild()` | `allow_self_join` parameter defaults to `True` | **Fixed** — default changed to `False` (Phase 2 deprecated self-join) | ✅ Done |
| `guilds.py` API `POST /guilds/create` | `allow_self_join` defaults to `True` | **Fixed** — default changed to `False` | ✅ Done |
| Any `console.log` / `print()` debug statements | Left from development | **Remove** — use proper logging (Python `logging` module, no `print()`) | ✅ Done |

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

Phase 1 moves classes/specs/roles/raids into **DB-driven expansion tables**
(not Python dict files). Clean up all hardcoded expansion data.

**Code to remove/refactor:**

| Location | What | Action | Status |
|----------|------|--------|--------|
| `app/constants.py` | Hardcoded `WOTLK_RAIDS`, `CLASS_ROLES`, `CLASS_SPECS` | **Remove** — data now lives in DB expansion tables; seed script populates it | ✅ Done |
| `WowClass` Python enum | Hardcoded class enum | **Keep** — still used as column type in Character model; removal requires schema migration | ⏳ Deferred |
| `src/constants.js` | Static `WOW_CLASSES`, `CLASS_ROLES`, `CLASS_SPECS`, `RAID_TYPES` | **Remove** — frontend fetches from v2 expansion endpoints; raids come from `expansion_raids` DB table | ✅ Done |
| Test files | Tests importing directly from `app/constants` for class/spec/raid data | **Update** to use the new DB-driven expansion registry or test helpers | ✅ Done |
| `meta.py` v1 constants endpoint | Hardcoded class/spec/raid response | **Refactored** — now queries DB expansion registry for expansion data | ✅ Done |
| `app/api/v1/admin.py`, `app/api/v2/meta.py`, `app/api/v2/admin_tenants.py` | Duplicated `_require_permission()` / `_require_admin()` | **Extracted** to shared `require_system_permission()` in `app/utils/api_helpers.py` | ✅ Done |
| `app/utils/class_roles.py` | Fallback to hardcoded `CLASS_ROLES` / `CLASS_SPECS` | **Removed** — fully DB-driven, no hardcoded fallbacks | ✅ Done |
| `app/seeds/expansions.py` | Imported `CLASS_SPECS` and `WowClass` from constants | **Self-contained** — all seed data inline, no constants imports | ✅ Done |
| `normalizeSpecName()` / `normalize_spec_name()` | Only prefix matching; "Feral Combat" ← "Combat" failed | **Fixed** — suffix + contains matching for full symmetry | ✅ Done |

**Dead code detection:**
```bash
# Find any remaining direct import of CLASS_ROLES, WOTLK_RAIDS from constants.py
grep -rn "from app.constants import.*CLASS_ROLES\|from app.constants import.*CLASS_SPECS\|from app.constants import.*WOTLK_RAIDS" app/ tests/
# Expected: empty — all references should use DB-driven expansion registry

# Find any remaining RAID_TYPES references in frontend
grep -rn "RAID_TYPES\|WOTLK_RAIDS" src/ --include="*.js" --include="*.vue"
# Expected: empty — raid types come from DB via expansion endpoints

# Verify WowClass enum is gone
grep -rn "WowClass" app/ tests/
# Expected: empty (or only in migration/seed scripts)
```

#### 13.3.3 Phase 2 Cleanup Checklist

Phase 2 replaces self-join with invitation-based guild membership.

**✅ Completed:**

| Location | What | Action | Status |
|----------|------|--------|--------|
| `Guild` model `allow_self_join` field | Boolean flag for direct join | **Deprecated** — field kept for DB compat, defaults to `False`, marked with `# DEPRECATED (Phase 2)` | ✅ Done |
| `POST /guilds/{id}/join` endpoint | Direct join without invitation | **Removed** — endpoint fully deleted from `app/api/v1/guilds.py` | ✅ Done |
| `guilds.js` API `joinGuild()` | API call for direct join | **Removed** — export deleted from `src/api/guilds.js` | ✅ Done |
| `GuildInvitation` model | Guild-level invitations | **Added** — `app/models/guild.py` with token, expiry, max_uses | ✅ Done |
| `GuildVisibility` enum | `OPEN`/`HIDDEN` guild visibility | **Added** — `app/enums.py`, used in Guild model and sidebar | ✅ Done |
| v2 guild invitation API | Send, accept, revoke, list invitations | **Added** — `app/api/v2/guild_invitations.py` | ✅ Done |
| v2 application API | Apply, approve, decline membership | **Added** — same file, with `MemberStatus.APPLIED`/`DECLINED` | ✅ Done |
| Guild discovery page | Browse open guilds within tenant | **Added** — `src/views/GuildDiscoveryView.vue` with route `/guilds/discover` | ✅ Done |
| Guild invitation management UI | Admin panel tab for invitations | **Added** — `src/components/admin/GuildInvitationsTab.vue` | ✅ Done |
| Sidebar hidden guild filter | Hidden guilds not in dropdown | **Added** — `visibleGuilds` computed in `AppSidebar.vue` | ✅ Done |

**Verification:**
```bash
# No references to allow_self_join in frontend (confirmed empty)
grep -rn "allow_self_join\|self.join\|self_join" src/ --include="*.vue" --include="*.js"
# Expected: empty ✅

# No direct join endpoints remaining (confirmed: only invitation-based)
grep -rn "join_guild" app/api/ --include="*.py"
# Expected: empty ✅

# joinGuild in frontend is ONLY for WebSocket room joining (not guild membership)
grep -rn "joinGuild" src/ --include="*.vue" --include="*.js"
# Expected: only useSocket.js references ✅
```

#### 13.3.4 Phase 3 Cleanup Checklist

Phase 3 introduces the class-role matrix, replacing static mappings.

**Status: ✅ COMPLETE**

**Code changes completed:**

| Location | What | Action | Status |
|----------|------|--------|--------|
| `app/models/guild.py` | `GuildClassRoleOverride` model | **Added** — per-guild class→role override with FK to `expansion_classes` | ✅ Done |
| `app/services/matrix_service.py` | Matrix resolver service | **Created** — `resolve_matrix()`, `is_role_allowed()`, `set_guild_overrides()`, `reset_guild_class()`, `reset_guild_matrix()` | ✅ Done |
| `app/api/v2/guild_matrix.py` | v2 matrix API endpoints | **Created** — GET/PUT/DELETE with `@require_guild_permission`, `_t()`, `validate_required()` | ✅ Done |
| `app/utils/class_roles.py` | Guild-scoped validation | **Updated** — `validate_class_role()` and `allowed_roles_for_class()` accept optional `guild_id` kwarg for matrix resolver | ✅ Done |
| `app/services/signup_service.py` | `_validate_class_role()` | **Updated** — passes `guild_id=character.guild_id` to `validate_class_role()` | ✅ Done |
| `app/services/lineup_service.py` | `_validate_class_role_lineup()` | **Updated** — passes `guild_id=character.guild_id` to `validate_class_role()` | ✅ Done |
| `app/services/character_service.py` | `_default_role_for_class()` | **Updated** — accepts optional `guild_id` kwarg, passes to `allowed_roles_for_class()` | ✅ Done |
| `app/seeds/permissions.py` | `manage_class_role_matrix` permission | **Added** to `guild_admin` and `global_admin` roles | ✅ Done |
| `src/components/admin/ClassRoleMatrixTab.vue` | Matrix editor UI | **Created** — uses `WowCard`, `WowButton`, `useI18n`, `useUiStore`, `useGuildStore`, guilds API | ✅ Done |
| `src/views/AdminPanelView.vue` | Matrix tab in admin panel | **Added** — registered as "matrix" tab with `manage_class_role_matrix` permission | ✅ Done |
| `src/api/guilds.js` | Matrix API functions | **Added** — `getClassRoleMatrix()`, `setClassRoleOverrides()`, `resetClassRoleOverrides()`, `resetClassRoleMatrix()` | ✅ Done |
| `translations/en.json` + `pl.json` | i18n keys | **Added** — `api.matrix.*` (backend) + `guild.matrix*` + `admin.tabs.classRoleMatrix` (frontend) | ✅ Done |
| `tests/test_class_role_matrix.py` | 31 tests | **Created** — model, service, API, integration tests | ✅ Done |

**Verification:**
```bash
# No hardcoded CLASS_ROLES validation in services
grep -rn "CLASS_ROLES\[" app/services/ --include="*.py"
# Expected: empty (all go through matrix resolver) ✅

# No hardcoded role strings in services (all use shared constants)
grep -rn '"main_tank"\|"off_tank"\|"healer"\|"melee_dps"\|"range_dps"' app/services/lineup_service.py app/services/signup_service.py
# Expected: empty ✅

# All 783 tests pass
python -m pytest tests/ -q
# 783 passed ✅

# Frontend builds
npx vite build
# ✓ built in 3.8s ✅
```

**Phase 3 SPOF cleanup — hardcoded role string removal:**

| Location | What | Action | Status |
|----------|------|--------|--------|
| `app/constants.py` | Shared role constants | **Added** — `ROLE_TO_GROUP`, `GROUP_TO_ROLE`, `LINEUP_GROUP_KEYS`, `DEFAULT_ROLE`, `DEFAULT_ROLE_SLOT_COUNTS`, `get_slot_counts_from_rd()` | ✅ Done |
| `src/constants.js` | Shared role constants | **Added** — `ROLE_TO_GROUP`, `GROUP_TO_ROLE`, `LINEUP_GROUP_KEYS`, `DEFAULT_ROLE`, `DEFAULT_ROLE_SLOT_COUNTS`, `ROLE_STYLE_MAP`, `ROLE_LABEL_CLASS`, `LINEUP_COLUMNS`, `ROLE_VALUES`, `ROLE_TO_SLOT_PROP`, `ROLE_BAR_CLASS` | ✅ Done |
| `app/services/lineup_service.py` | Hardcoded role strings | **Replaced** — imports `ROLE_TO_GROUP`, `GROUP_TO_ROLE`, `LINEUP_GROUP_KEYS`, `DEFAULT_ROLE`, `get_slot_counts_from_rd()` | ✅ Done |
| `app/services/signup_service.py` | Hardcoded slot defaults | **Replaced** — uses `get_slot_counts_from_rd()` | ✅ Done |
| `src/components/common/RoleBadge.vue` | Hardcoded CSS switch | **Replaced** — uses `ROLE_STYLE_MAP` from shared constants | ✅ Done |
| `src/components/raids/LineupBoard.vue` | Hardcoded role strings (30+ occurrences) | **Replaced** — uses `LINEUP_COLUMNS`, `ROLE_TO_GROUP`, `LINEUP_GROUP_KEYS`, `DEFAULT_ROLE`, `ROLE_TO_SLOT_PROP`, `applyLineupData()` helper | ✅ Done |
| `src/components/raids/SignupForm.vue` | Hardcoded `availableRoles` default | **Replaced** — uses `ROLE_VALUES` from constants | ✅ Done |
| `src/components/raids/SignupList.vue` | Hardcoded `availableRoles` default | **Replaced** — uses `ROLE_VALUES` from constants | ✅ Done |
| `src/components/raids/CompositionSummary.vue` | Hardcoded role summary | **Replaced** — uses `ROLE_OPTIONS`, `ROLE_TO_SLOT_PROP`, `ROLE_BAR_CLASS`, `DEFAULT_ROLE_SLOT_COUNTS` | ✅ Done |
| `src/components/admin/DefaultRaidDefinitionsTab.vue` | Hardcoded slot defaults | **Replaced** — uses `DEFAULT_ROLE_SLOT_COUNTS`, `ROLE_VALUES` | ✅ Done |

#### 13.3.5 Phase 4 Cleanup Checklist

Phase 4 adds multi-expansion support and per-guild realm customization.
WotLK-only assumptions and hardcoded realm lists must go.

**Code to remove/refactor:**

| Location | What | Action | Status |
|----------|------|--------|--------|
| `src/constants.js` static `WOW_CLASSES` | Hardcoded 10 WotLK classes | **Remove** — frontend gets classes from constants store which fetches from expansion-aware backend | ✅ Done |
| `src/constants.js` static `RAID_TYPES` | Hardcoded 8 WotLK raids | **Remove** — same as above | ✅ Done |
| `src/constants.js` `WARMANE_REALMS` | Hardcoded Warmane realm list | **Remove** — realms are now per-guild configurable; character creation reads from guild's realm list | ✅ Done (Phase 5) |
| `app/constants.py` `WARMANE_REALMS` | Hardcoded Warmane realm list | ✅ **Moved** to Warmane plugin (`app/plugins/warmane/plugin.py`). Re-export kept for backwards compatibility | ✅ Done → fully removed in Phase 5 |
| `CharacterManagerView.vue` | Static class dropdown from `WOW_CLASSES` | **Replace** with guild-scoped expansion data via `getGuildConstants()` API | ✅ Done |
| `CharacterManagerView.vue` | Static realm dropdown from `WARMANE_REALMS` | **Replace** with guild-specific realm list from guild realms API | ✅ Done |
| `app/constants.py` | Any remaining re-exports or hardcoded expansion data | **Remove entirely** if all data lives in DB expansion tables | ✅ Done — no expansion data in constants.py |
| Phase 1 compat shims | Anything marked `# COMPAT: Remove in Phase 4` | **Remove now** | ✅ Done — no COMPAT shims remain |
| `app/enums.py` `WowClass` | Hardcoded WoW class enum | **Remove** — all validation is DB-driven | ✅ Done |

**Verification:**
```bash
# No hardcoded WoW class lists in frontend
grep -rn "Death Knight.*Druid.*Hunter\|WOW_CLASSES.*=.*\[" src/ --include="*.js" --include="*.vue"
# Expected: empty (classes come from DB via API)

# No WotLK-only raid types in frontend
grep -rn "naxx\|ulduar\|icc" src/ --include="*.js" --include="*.vue" | grep -v "constants.js"
# Expected: empty (raid types come from backend)

# No hardcoded realm lists
grep -rn "WARMANE_REALMS\|Icecrown.*Lordaeron" src/ app/ --include="*.js" --include="*.vue" --include="*.py"
# Expected: empty (realms come from guild settings)
```

#### 13.3.6 Phase 5 Cleanup Checklist

Phase 5 creates a generic, server-agnostic armory plugin and wraps Discord as a plugin.

**Code to remove/refactor:**

| Location | What | Action | Status |
|----------|------|--------|--------|
| `app/services/armory/warmane.py` | Warmane-specific API parser | Kept as provider implementation detail inside `app/services/armory/`. Not part of the plugin. | Provider pattern ✅ |
| `app/services/discord_service.py` | Direct Discord integration | Auth-layer integration. Plugin wraps metadata. | ✅ Plugin created (`app/plugins/discord/`) |
| `src/api/warmane.js` | Frontend Warmane API module | Kept — used by existing components for armory sync | Deferred |
| `src/api/armory.js` | Frontend armory API module | Kept — used by armory config management | Deferred |
| `app/api/v1/warmane.py` | Warmane blueprint | Kept in v1 registration — plugin does not re-register | Deferred |
| `WARMANE_REALMS` everywhere | Hardcoded realm lists | ✅ **Removed entirely** — zero references in codebase. Realms are dynamic (from provider API or manual per-guild config) | ✅ Done |
| `app/seeds/permissions.py` | Missing `manage_plugins` permission | ✅ **Added** — `manage_plugins` in permissions seed, assigned to `global_admin` role | ✅ Done |
| `app/api/v2/plugins.py` | Plugin config endpoint missing authorization | ✅ **Fixed** — `get_plugin_config` now requires `manage_plugins` via `require_system_permission()` | ✅ Done |
| `useWowheadTooltips.js` | Inline Wowhead script injection | **Consider** moving to plugin if Wowhead integration becomes optional | Deferred |

**Verification:**
```bash
# No hardcoded realm lists anywhere
grep -rn "WARMANE_REALMS\|warmaneRealms\|warmane_realms" src/ app/ --include="*.js" --include="*.vue" --include="*.py"
# Expected: empty ✅

# Armory plugin has zero server-specific references
grep -rn -i "warmane" app/plugins/ --include="*.py"
# Expected: empty ✅
```

#### 13.3.7 Phase 6 Cleanup Checklist

Phase 6 adds billing. Clean up hardcoded plan defaults.

**Code to remove/refactor:**

| Location | What | Action |
|----------|------|--------|
| `Tenant` model `max_guilds` default=3, `max_members` unlimited | Hardcoded limits | **Replace** with limits from billing/subscription model. Defaults should come from plan definition, not model defaults |
| `tenant_service.py` guild limit check | `if guild_count >= tenant.max_guilds` | **Replace** with `billing_service.check_limit(tenant, 'guilds')` if billing manages limits |
| Phase 0 manual limit checks | Anywhere `tenant.max_guilds` is checked directly | **Consolidate** into billing service |
| `/api/v1/` blueprints | All v1 endpoints | **Deprecation review** — assess if v1 can be fully removed now that v2 is stable, or if legacy integrations still need it. Remove if safe. |

**Final full-codebase audit (see §13.4):**
```bash
# Run all verification commands from all previous phases
# Confirm zero orphans, zero dead imports, zero stale tests
# Verify no v1 endpoints are still referenced by frontend (all should use v2)
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
| 3 | `allow_self_join` on Guild model | **Deprecated** — field kept for DB compat, defaults to `False`, `POST /guilds/{id}/join` endpoint removed | **Phase 2** ✅ | Deprecated; direct-join endpoint removed; `joinGuild` API removed from frontend |
| 4 | Static `WOW_CLASSES` in `src/constants.js` | Active — hardcoded 10 WotLK classes | **Phase 1** | Remove when DB-driven expansion data replaces it |
| 5 | `WowClass` Python enum in `app/enums.py` | Active — hardcoded class enum | **Phase 1** | Remove when DB-driven `expansion_classes` table replaces it |
| 6 | `CLASS_ROLES` / `CLASS_SPECS` in `app/constants.py` | Active — hardcoded WotLK mappings | **Phase 1** | Remove when DB-driven expansion registry replaces it |
| 7 | Static `WARMANE_REALMS` in `src/constants.js` + `app/constants.py` | ✅ **Removed entirely** — zero references in codebase | **Phase 5** | Realms are fully dynamic: fetched from provider API or managed manually per-guild via GuildRealmsTab |
| 8 | `i18n-plan.md` | Planning doc — may become stale | **Phase 0** | Review; integrate remaining items into this plan or archive |
| 9 | Hardcoded `max_guilds=3`, `max_members=unlimited` on Tenant model | Will be introduced in Phase 0 | **Phase 6** | Replace with billing-managed plan limits |
| 10 | Database file `wotlk_calendar.db` | Active — WotLK-specific name | **Phase 0** | Rename to `raid_calendar.db` |
| 11 | `/api/v1/` endpoints | Active — all current API | **Phase 6** | Review for removal after all frontend migrates to v2 |
| 12 | `JobQueue` table without `tenant_id` | Active — global queue | **Phase 0** | Add `tenant_id` column; scope all job handlers |
