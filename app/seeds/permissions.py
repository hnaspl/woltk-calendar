"""Seed default system roles, permissions, and grant rules."""

from __future__ import annotations

import logging

from app.extensions import db
from app.models.permission import SystemRole, Permission, RolePermission, RoleGrantRule

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default roles (name, display_name, description, level)
# ---------------------------------------------------------------------------
DEFAULT_ROLES = [
    ("global_admin", "Global Admin", "System-wide administrator with full access", 100),
    ("tenant_admin", "Tenant Admin", "Tenant workspace administrator with full tenant management access", 90),
    ("guild_admin", "Guild Admin", "Full guild control including role management", 80),
    ("officer", "Officer", "Can manage events, lineup, members, and attendance", 60),
    ("raid_leader", "Raid Leader", "Can manage lineup and signups for events", 40),
    ("member", "Member", "Basic guild member with signup access", 20),
]

# ---------------------------------------------------------------------------
# All permissions (code, display_name, description, category)
# ---------------------------------------------------------------------------
ALL_PERMISSIONS = [
    # Events
    ("view_events", "View Events", "View raid events, schedules, and event details on the calendar", "events"),
    ("create_events", "Create Events", "Create new raid events on the calendar with date, time, and raid settings", "events"),
    ("edit_events", "Edit Events", "Modify existing raid event details such as title, time, description, and settings", "events"),
    ("delete_events", "Delete Events", "Permanently remove raid events from the calendar", "events"),
    ("lock_signups", "Lock Signups", "Lock or unlock event signups to prevent or allow new character registrations", "events"),
    ("cancel_events", "Cancel Events", "Mark events as cancelled or completed, preventing further changes", "events"),
    ("duplicate_events", "Duplicate Events", "Create a copy of an existing event with a new date and optional signup transfer", "events"),

    # Signups
    ("sign_up", "Sign Up", "Register own characters for upcoming raid events", "signups"),
    ("view_signups", "View Signups", "View detailed signup lists including other players' characters and their status", "signups"),
    ("delete_own_signup", "Delete Own Signup", "Remove own character signup from an event before it starts", "signups"),
    ("decline_own_signup", "Decline Own Signup", "Decline a lineup placement when assigned by a raid leader", "signups"),
    ("manage_signups", "Manage Signups", "Decline, remove, or modify other players' signups and lineup assignments", "signups"),
    ("ban_characters", "Ban Characters", "Temporarily or permanently ban characters from signing up for events", "signups"),
    ("unban_characters", "Unban Characters", "Remove existing character bans to allow them to sign up again", "signups"),
    ("request_replacement", "Request Replacement", "Request a character replacement when unable to attend a confirmed raid", "signups"),

    # Lineup
    ("update_lineup", "Update Lineup", "Assign characters to raid lineup positions and manage bench queue", "lineup"),
    ("confirm_lineup", "Confirm Lineup", "Finalize and lock the raid lineup before the event starts", "lineup"),
    ("reorder_bench", "Reorder Bench", "Change the priority order of characters on the bench waiting list", "lineup"),

    # Characters
    ("manage_own_characters", "Manage Own Characters", "Add, edit, or remove own characters including class, spec, and gear updates", "characters"),
    ("view_member_characters", "View Member Characters", "View other guild members' character profiles and equipment details", "characters"),

    # Attendance
    ("view_attendance", "View Attendance", "View attendance records, history, and statistics for past events", "attendance"),
    ("record_attendance", "Record Attendance", "Record who attended, was late, or missed a raid after it completes", "attendance"),

    # Raid definitions & templates (guild-scoped)
    ("manage_raid_definitions", "Manage Guild Raid Definitions", "Create, edit, and delete guild-specific raid definitions with size and difficulty settings", "definitions"),
    ("manage_default_definitions", "Manage Default Definitions", "Edit or delete the built-in global raid definitions shared across all guilds", "definitions"),
    ("manage_templates", "Manage Guild Templates", "Create, edit, and delete reusable event templates for quick raid scheduling", "definitions"),
    ("manage_series", "Manage Guild Series", "Create, edit, and delete recurring event series with day-of-week scheduling", "definitions"),

    # Guild management
    ("create_guild", "Create Guild", "Create new guilds within the tenant workspace", "guild"),
    ("view_guild", "View Guild", "View guild information, member list, and guild settings", "guild"),
    ("update_guild_settings", "Update Guild Settings", "Modify guild name, realm, expansion, and other configuration options", "guild"),
    ("delete_guild", "Delete Guild", "Permanently delete the guild and all associated data", "guild"),
    ("add_members", "Add Members", "Directly add new members to the guild without an invitation", "guild"),
    ("remove_members", "Remove Members", "Remove members from the guild, revoking their access", "guild"),
    ("update_member_roles", "Update Member Roles", "Change guild member roles to grant or restrict permissions", "guild"),
    ("manage_guild_roles", "Manage Guild Roles", "Create, edit, and delete custom guild roles with specific permission sets", "guild"),
    ("invite_members", "Invite Members", "Send guild invitations to users within the tenant workspace", "guild"),
    ("approve_applications", "Approve Applications", "Review and approve or decline guild membership applications", "guild"),
    ("manage_guild_visibility", "Manage Guild Visibility", "Control whether the guild is visible to other tenant members for joining", "guild"),
    ("manage_class_role_matrix", "Manage Class-Role Matrix", "Configure which WoW classes can fill which raid roles (tank, healer, DPS)", "guild"),
    ("manage_guild_expansions", "Manage Guild Expansions", "Enable or disable WoW expansion packs available for the guild's raids", "guild"),
    ("manage_guild_realms", "Manage Guild Realms", "Configure the guild's realm list for character armory lookups", "guild"),

    # Notifications
    ("view_notifications", "View Notifications", "View personal notifications about signups, raids, and guild activity", "notifications"),

    # Tenant management
    ("manage_tenant_members", "Manage Tenant Members", "Invite, remove, and manage members across the entire tenant workspace", "tenant"),
    ("manage_tenant_settings", "Manage Tenant Settings", "Change tenant workspace name, limits, plan, and configuration", "tenant"),
    ("manage_tenants", "Manage Tenants", "Global admin: view, suspend, rename, or delete any tenant workspace in the system", "tenant"),

    # Admin
    ("manage_expansions", "Manage Expansions", "Global admin: add, edit, or disable WoW expansion packs system-wide", "admin"),
    ("manage_plugins", "Manage Plugins", "Global admin: enable or disable system plugins and integrations", "admin"),
    ("list_system_users", "List System Users", "View all registered users across the entire system with their status", "admin"),
    ("manage_system_users", "Manage System Users", "Activate, deactivate, verify, or delete user accounts system-wide", "admin"),
    ("trigger_sync", "Trigger Sync", "Manually trigger character data synchronization from the armory", "admin"),
    ("manage_autosync", "Manage Auto-Sync", "Configure automatic armory sync intervals and enable/disable auto-sync", "admin"),
    ("manage_roles", "Manage Roles", "Create, edit, and delete system-wide roles and their permission assignments", "admin"),
    ("manage_system_settings", "Manage System Settings", "Configure global system settings including SMTP, password policy, and integrations", "admin"),

    # Billing & plans
    ("manage_plans", "Manage Plans", "Create, edit, and delete subscription plans with feature limits and pricing", "billing"),
    ("manage_billing", "Manage Billing", "View and manage tenant billing, subscription status, and payment history", "billing"),
]

# ---------------------------------------------------------------------------
# Role → Permission assignments
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS = {
    "member": [
        "view_events", "sign_up", "delete_own_signup", "decline_own_signup",
        "manage_own_characters", "view_attendance", "view_guild",
        "view_notifications",
    ],
    "raid_leader": [
        # Inherits member permissions +
        "view_events", "sign_up", "delete_own_signup", "decline_own_signup",
        "manage_own_characters", "view_attendance", "view_guild",
        "view_notifications",
        # Raid leader specifics
        "view_signups",
        "update_lineup", "confirm_lineup", "reorder_bench",
        "manage_signups", "ban_characters", "unban_characters",
        "request_replacement", "view_member_characters",
    ],
    "officer": [
        # Inherits raid_leader permissions +
        "view_events", "sign_up", "delete_own_signup", "decline_own_signup",
        "manage_own_characters", "view_attendance", "view_guild",
        "view_notifications",
        "view_signups",
        "update_lineup", "confirm_lineup", "reorder_bench",
        "manage_signups", "ban_characters", "unban_characters",
        "request_replacement", "view_member_characters",
        # Officer specifics
        "create_events", "edit_events", "delete_events",
        "lock_signups", "cancel_events", "duplicate_events",
        "record_attendance",
        "manage_raid_definitions", "manage_templates", "manage_series",
        "add_members", "remove_members", "update_member_roles",
        "invite_members", "approve_applications",
    ],
    "guild_admin": [
        # All officer permissions +
        "view_events", "sign_up", "delete_own_signup", "decline_own_signup",
        "manage_own_characters", "view_attendance", "view_guild",
        "view_notifications",
        "view_signups",
        "update_lineup", "confirm_lineup", "reorder_bench",
        "manage_signups", "ban_characters", "unban_characters",
        "request_replacement", "view_member_characters",
        "create_events", "edit_events", "delete_events",
        "lock_signups", "cancel_events", "duplicate_events",
        "record_attendance",
        "manage_raid_definitions", "manage_templates", "manage_series",
        "add_members", "remove_members", "update_member_roles",
        "invite_members", "approve_applications", "manage_guild_visibility",
        "manage_class_role_matrix", "update_guild_settings",
        # Guild admin specifics (create_guild/delete_guild are tenant-level,
        # not guild-level — moved to tenant_admin to prevent guild_admin
        # users from creating unlimited guilds across tenants)
        "manage_guild_roles",
        "manage_guild_expansions", "manage_guild_realms",
    ],
    "tenant_admin": [
        # All guild_admin permissions +
        "view_events", "sign_up", "delete_own_signup", "decline_own_signup",
        "manage_own_characters", "view_attendance", "view_guild",
        "view_notifications",
        "view_signups",
        "update_lineup", "confirm_lineup", "reorder_bench",
        "manage_signups", "ban_characters", "unban_characters",
        "request_replacement", "view_member_characters",
        "create_events", "edit_events", "delete_events",
        "lock_signups", "cancel_events", "duplicate_events",
        "record_attendance",
        "manage_raid_definitions", "manage_templates", "manage_series",
        "add_members", "remove_members", "update_member_roles",
        "invite_members", "approve_applications", "manage_guild_visibility",
        "manage_class_role_matrix", "update_guild_settings",
        "create_guild", "delete_guild", "manage_guild_roles",
        "manage_guild_expansions", "manage_guild_realms",
        "manage_tenant_members", "manage_tenant_settings",
        # Tenant admin specifics
        "manage_billing",
    ],
    "global_admin": [
        # All permissions
        "view_events", "sign_up", "delete_own_signup", "decline_own_signup",
        "manage_own_characters", "view_attendance", "view_guild",
        "view_notifications",
        "view_signups",
        "update_lineup", "confirm_lineup", "reorder_bench",
        "manage_signups", "ban_characters", "unban_characters",
        "request_replacement", "view_member_characters",
        "create_events", "edit_events", "delete_events",
        "lock_signups", "cancel_events", "duplicate_events",
        "record_attendance",
        "manage_raid_definitions", "manage_default_definitions",
        "manage_templates", "manage_series",
        "add_members", "remove_members", "update_member_roles",
        "invite_members", "approve_applications", "manage_guild_visibility",
        "manage_class_role_matrix", "update_guild_settings",
        "create_guild", "delete_guild", "manage_roles", "manage_guild_roles",
        "manage_guild_expansions", "manage_guild_realms",
        "list_system_users", "manage_system_users",
        "trigger_sync", "manage_autosync",
        "manage_system_settings",
        # Tenant management (global admin can manage all tenants)
        "manage_tenant_members", "manage_tenant_settings", "manage_tenants",
        "manage_expansions",
        "manage_plugins",
        "manage_plans",
        "manage_billing",
    ],
}

# ---------------------------------------------------------------------------
# Grant rules: which role can assign which role
# ---------------------------------------------------------------------------
GRANT_RULES = {
    "global_admin": ["tenant_admin", "guild_admin", "officer", "raid_leader", "member"],
    "tenant_admin": ["guild_admin", "officer", "raid_leader", "member"],
    "guild_admin": ["guild_admin", "officer", "raid_leader", "member"],
    "officer": ["raid_leader", "member"],
}


def seed_permissions() -> int:
    """Seed default roles, permissions, and grant rules. Returns count of roles created."""
    created = 0

    # 1. Create permissions
    perm_map: dict[str, Permission] = {}
    for code, display_name, description, category in ALL_PERMISSIONS:
        existing = db.session.execute(
            db.select(Permission).where(Permission.code == code)
        ).scalar_one_or_none()
        if existing:
            perm_map[code] = existing
        else:
            p = Permission(
                code=code,
                display_name=display_name,
                description=description,
                category=category,
            )
            db.session.add(p)
            db.session.flush()
            perm_map[code] = p

    # 2. Create roles
    role_map: dict[str, SystemRole] = {}
    for name, display_name, description, level in DEFAULT_ROLES:
        existing = db.session.execute(
            db.select(SystemRole).where(SystemRole.name == name)
        ).scalar_one_or_none()
        if existing:
            role_map[name] = existing
        else:
            r = SystemRole(
                name=name,
                display_name=display_name,
                description=description,
                level=level,
                is_system=True,
            )
            db.session.add(r)
            db.session.flush()
            role_map[name] = r
            created += 1

    # 3. Assign permissions to roles
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = role_map.get(role_name)
        if role is None:
            continue
        for code in perm_codes:
            perm = perm_map.get(code)
            if perm is None:
                continue
            existing = db.session.execute(
                db.select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            ).scalar_one_or_none()
            if not existing:
                db.session.add(RolePermission(role_id=role.id, permission_id=perm.id))

    # 4. Create grant rules
    for granter_name, grantee_names in GRANT_RULES.items():
        granter = role_map.get(granter_name)
        if granter is None:
            continue
        for grantee_name in grantee_names:
            grantee = role_map.get(grantee_name)
            if grantee is None:
                continue
            existing = db.session.execute(
                db.select(RoleGrantRule).where(
                    RoleGrantRule.granter_role_id == granter.id,
                    RoleGrantRule.grantee_role_id == grantee.id,
                )
            ).scalar_one_or_none()
            if not existing:
                db.session.add(
                    RoleGrantRule(granter_role_id=granter.id, grantee_role_id=grantee.id)
                )

    db.session.commit()
    return created
