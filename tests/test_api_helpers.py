"""Unit tests for api_helpers and decorators modules."""

from __future__ import annotations

import json

import pytest

from app.utils.api_helpers import (
    build_guild_role_map,
    get_event_or_404,
    get_json,
    validate_required,
)
from app.utils.decorators import require_guild_permission


# ---------------------------------------------------------------------------
# get_json
# ---------------------------------------------------------------------------


class TestGetJson:
    def test_returns_parsed_json(self, app):
        with app.test_request_context(
            content_type="application/json",
            data=json.dumps({"a": 1}),
        ):
            assert get_json() == {"a": 1}

    def test_returns_empty_dict_for_no_body(self, app):
        with app.test_request_context():
            assert get_json() == {}

    def test_returns_empty_dict_for_invalid_json(self, app):
        with app.test_request_context(
            content_type="application/json",
            data="not-json",
        ):
            assert get_json() == {}


# ---------------------------------------------------------------------------
# validate_required
# ---------------------------------------------------------------------------


class TestValidateRequired:
    def test_returns_none_when_all_present(self, app):
        with app.test_request_context():
            result = validate_required({"a": 1, "b": 2}, "a", "b")
            assert result is None

    def test_returns_error_when_missing(self, app):
        with app.test_request_context():
            result = validate_required({"a": 1}, "a", "b")
            assert result is not None
            response, status = result
            assert status == 400

    def test_returns_none_for_empty_fields(self, app):
        with app.test_request_context():
            result = validate_required({"a": 1})
            assert result is None


# ---------------------------------------------------------------------------
# get_event_or_404
# ---------------------------------------------------------------------------


class TestGetEventOr404:
    def test_returns_event_when_found(self, db, ctx, seed):
        event = seed["event"]
        guild = seed["guild"]
        result, err = get_event_or_404(guild.id, event.id)
        assert err is None
        assert result.id == event.id

    def test_returns_error_for_wrong_guild(self, db, ctx, seed):
        event = seed["event"]
        result, err = get_event_or_404(9999, event.id)
        assert result is None
        assert err is not None
        _, status = err
        assert status == 404

    def test_returns_error_for_missing_event(self, db, ctx, seed):
        guild = seed["guild"]
        result, err = get_event_or_404(guild.id, 9999)
        assert result is None
        assert err is not None
        _, status = err
        assert status == 404


# ---------------------------------------------------------------------------
# build_guild_role_map
# ---------------------------------------------------------------------------


class TestBuildGuildRoleMap:
    def test_empty_user_ids(self, db, ctx, seed):
        guild = seed["guild"]
        assert build_guild_role_map(guild.id, []) == {}

    def test_returns_map_for_members(self, db, ctx, seed):
        from app.models.guild import GuildMembership

        guild = seed["guild"]
        user1 = seed["user1"]

        # Create a membership
        m = GuildMembership(
            guild_id=guild.id, user_id=user1.id,
            role="member", status="active",
        )
        db.session.add(m)
        db.session.commit()

        result = build_guild_role_map(guild.id, [user1.id])
        assert user1.id in result
        assert result[user1.id]["role"] == "member"


# ---------------------------------------------------------------------------
# require_guild_permission decorator
# ---------------------------------------------------------------------------


class TestRequireGuildPermission:
    def test_rejects_when_no_membership(self, app, db, ctx, seed):
        """Decorator returns 403 when user has no guild membership."""
        from unittest.mock import patch, MagicMock

        guild = seed["guild"]

        @require_guild_permission()
        def handler(guild_id, membership):
            return {"ok": True}

        with app.test_request_context():
            mock_user = MagicMock()
            mock_user.id = 9999
            mock_user.is_admin = False
            with patch("app.utils.decorators.current_user", mock_user):
                resp = handler(guild_id=guild.id)
            assert resp[1] == 403

    def test_allows_when_member(self, app, db, ctx, seed):
        """Decorator passes when user has guild membership."""
        from unittest.mock import patch, MagicMock
        from app.models.guild import GuildMembership

        guild = seed["guild"]
        user1 = seed["user1"]

        m = GuildMembership(
            guild_id=guild.id, user_id=user1.id,
            role="member", status="active",
        )
        db.session.add(m)
        db.session.commit()

        @require_guild_permission()
        def handler(guild_id, membership):
            return {"ok": True, "has_membership": membership is not None}

        with app.test_request_context():
            mock_user = MagicMock()
            mock_user.id = user1.id
            mock_user.is_admin = False
            with patch("app.utils.decorators.current_user", mock_user):
                result = handler(guild_id=guild.id)
            assert result == {"ok": True, "has_membership": True}

    def test_rejects_when_permission_missing(self, app, db, ctx, seed):
        """Decorator returns 403 when member lacks required permission."""
        from unittest.mock import patch, MagicMock
        from app.models.guild import GuildMembership

        guild = seed["guild"]
        user1 = seed["user1"]

        m = GuildMembership(
            guild_id=guild.id, user_id=user1.id,
            role="member", status="active",
        )
        db.session.add(m)
        db.session.commit()

        @require_guild_permission("some_nonexistent_permission")
        def handler(guild_id, membership):
            return {"ok": True}

        with app.test_request_context():
            mock_user = MagicMock()
            mock_user.id = user1.id
            mock_user.is_admin = False
            with patch("app.utils.decorators.current_user", mock_user):
                resp = handler(guild_id=guild.id)
            assert resp[1] == 403

    def test_admin_bypasses_permission(self, app, db, ctx, seed):
        """Site admin bypasses permission check even without membership."""
        from unittest.mock import patch, MagicMock

        guild = seed["guild"]

        @require_guild_permission("some_permission")
        def handler(guild_id, membership):
            return {"ok": True}

        with app.test_request_context():
            mock_user = MagicMock()
            mock_user.id = 9999
            mock_user.is_admin = True
            with patch("app.utils.decorators.current_user", mock_user), \
                 patch("app.utils.permissions.current_user", mock_user):
                result = handler(guild_id=guild.id)
            assert result == {"ok": True}
