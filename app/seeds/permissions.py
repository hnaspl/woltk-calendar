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
    ("view_events", "View Events", "View raid events and schedules", "events"),
    ("create_events", "Create Events", "Create new raid events", "events"),
    ("edit_events", "Edit Events", "Edit existing raid events", "events"),
    ("delete_events", "Delete Events", "Delete raid events", "events"),
    ("lock_signups", "Lock Signups", "Lock/unlock event signups", "events"),
    ("cancel_events", "Cancel Events", "Cancel or complete events", "events"),
    ("duplicate_events", "Duplicate Events", "Duplicate existing events", "events"),

    # Signups
    ("sign_up", "Sign Up", "Sign up for raid events", "signups"),
    ("view_signups", "View Signups", "View other players' signups and signup details", "signups"),
    ("delete_own_signup", "Delete Own Signup", "Remove own signup from events", "signups"),
    ("decline_own_signup", "Decline Own Signup", "Decline own lineup placement", "signups"),
    ("manage_signups", "Manage Signups", "Decline/delete other players' signups", "signups"),
    ("ban_characters", "Ban Characters", "Ban characters from events", "signups"),
    ("unban_characters", "Unban Characters", "Remove character bans", "signups"),
    ("request_replacement", "Request Replacement", "Request character replacement for signups", "signups"),

    # Lineup
    ("update_lineup", "Update Lineup", "Manage raid lineup and bench", "lineup"),
    ("confirm_lineup", "Confirm Lineup", "Confirm final raid lineup", "lineup"),
    ("reorder_bench", "Reorder Bench", "Reorder bench queue positions", "lineup"),

    # Characters
    ("manage_own_characters", "Manage Own Characters", "Add/edit/remove own characters", "characters"),
    ("view_member_characters", "View Member Characters", "View other members' characters", "characters"),

    # Attendance
    ("view_attendance", "View Attendance", "View attendance records", "attendance"),
    ("record_attendance", "Record Attendance", "Record raid attendance", "attendance"),

    # Raid definitions & templates (guild-scoped)
    ("manage_raid_definitions", "Manage Guild Raid Definitions", "Create/edit/delete guild-scoped raid definitions", "definitions"),
    ("manage_default_definitions", "Manage Default Definitions", "Edit/delete built-in (seeded) global raid definitions", "definitions"),
    ("manage_templates", "Manage Guild Templates", "Create/edit/delete guild-scoped event templates", "definitions"),
    ("manage_series", "Manage Guild Series", "Create/edit/delete guild-scoped recurring event series", "definitions"),

    # Guild management
    ("create_guild", "Create Guild", "Create new guilds", "guild"),
    ("view_guild", "View Guild", "View guild information", "guild"),
    ("update_guild_settings", "Update Guild Settings", "Modify guild settings", "guild"),
    ("delete_guild", "Delete Guild", "Delete the guild", "guild"),
    ("add_members", "Add Members", "Add new members to guild", "guild"),
    ("remove_members", "Remove Members", "Remove members from guild", "guild"),
    ("update_member_roles", "Update Member Roles", "Change member roles", "guild"),
    ("manage_guild_roles", "Manage Guild Roles", "Create/edit/delete guild-scoped roles and permissions", "guild"),
    ("invite_members", "Invite Members", "Send guild invitations within tenant", "guild"),
    ("approve_applications", "Approve Applications", "Approve/decline membership applications", "guild"),
    ("manage_guild_visibility", "Manage Guild Visibility", "Change guild visibility within tenant", "guild"),
    ("manage_class_role_matrix", "Manage Class-Role Matrix", "Edit class-role assignment matrix for guild", "guild"),
    ("manage_guild_expansions", "Manage Guild Expansions", "Enable/disable expansion packs for guild", "guild"),
    ("manage_guild_realms", "Manage Guild Realms", "Configure guild's realm list", "guild"),

    # Notifications
    ("view_notifications", "View Notifications", "View own notifications", "notifications"),

    # Tenant management
    ("manage_tenant_members", "Manage Tenant Members", "Invite/remove members from tenant workspace", "tenant"),
    ("manage_tenant_settings", "Manage Tenant Settings", "Change tenant name, limits, and settings", "tenant"),
    ("manage_tenants", "Manage Tenants", "Global admin: view/suspend/delete any tenant", "tenant"),

    # Admin
    ("manage_expansions", "Manage Expansions", "Global admin: add/edit/disable expansion packs", "admin"),
    ("manage_plugins", "Manage Plugins", "Global admin: enable/disable system plugins", "admin"),
    ("list_system_users", "List System Users", "View all system users", "admin"),
    ("manage_system_users", "Manage System Users", "Activate/deactivate/delete users", "admin"),
    ("trigger_sync", "Trigger Sync", "Trigger character synchronization", "admin"),
    ("manage_autosync", "Manage Auto-Sync", "Configure auto-sync settings", "admin"),
    ("manage_roles", "Manage Roles", "Create/edit/delete roles and permissions", "admin"),
    ("manage_system_settings", "Manage System Settings", "Configure global system settings", "admin"),

    # Billing & plans
    ("manage_plans", "Manage Plans", "Create, edit, and delete subscription plans", "billing"),
    ("manage_billing", "Manage Billing", "View and manage tenant billing", "billing"),
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
        # Guild admin specifics
        "create_guild", "delete_guild", "manage_guild_roles",
        "manage_guild_expansions", "manage_guild_realms",
        # Tenant management (guild admin = tenant admin for their workspace)
        "manage_tenant_members", "manage_tenant_settings",
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
