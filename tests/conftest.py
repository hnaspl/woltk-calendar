"""Shared test fixtures for the WotLK Calendar test suite."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.guild import Guild
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidEvent
from app.models.signup import Signup


@pytest.fixture(scope="session")
def app():
    """Create the Flask application for the test session."""
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
        "CORS_ORIGINS": ["*"],
        "SCHEDULER_ENABLED": False,
    })
    yield application


@pytest.fixture(autouse=True)
def db(app):
    """Create all tables before each test and drop them after."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def ctx(app):
    """Push an application context for service-level tests."""
    with app.app_context():
        yield


@pytest.fixture
def seed(db, ctx):
    """Create seed data: guild, 2 users, raid definition, raid event with 2 DPS slots."""
    guild = Guild(name="Test Guild", realm_name="Icecrown", created_by=None)
    db.session.add(guild)
    db.session.flush()

    user1 = User(username="player1", email="p1@test.com", password_hash="x", is_active=True)
    user2 = User(username="player2", email="p2@test.com", password_hash="x", is_active=True)
    user3 = User(username="player3", email="p3@test.com", password_hash="x", is_active=True)
    db.session.add_all([user1, user2, user3])
    db.session.flush()

    # Characters: all Hunters (allowed role: dps only)
    char1 = Character(
        user_id=user1.id, guild_id=guild.id, realm_name="Icecrown",
        name="HunterOne", class_name="Hunter", is_main=True, is_active=True,
    )
    char2 = Character(
        user_id=user2.id, guild_id=guild.id, realm_name="Icecrown",
        name="HunterTwo", class_name="Hunter", is_main=True, is_active=True,
    )
    char3 = Character(
        user_id=user3.id, guild_id=guild.id, realm_name="Icecrown",
        name="HunterThree", class_name="Hunter", is_main=False, is_active=True,
    )
    db.session.add_all([char1, char2, char3])
    db.session.flush()

    # Raid definition with only 2 DPS slots for testing bench mechanics
    raid_def = RaidDefinition(
        guild_id=guild.id, code="test_raid", name="Test Raid",
        default_raid_size=2,
        dps_slots=2, main_tank_slots=0, off_tank_slots=0,
        tank_slots=0, healer_slots=0,
    )
    db.session.add(raid_def)
    db.session.flush()

    now = datetime.now(timezone.utc)
    event = RaidEvent(
        guild_id=guild.id, title="Test Raid Night",
        realm_name="Icecrown", raid_size=2, difficulty="normal",
        starts_at_utc=now + timedelta(hours=24),
        ends_at_utc=now + timedelta(hours=27),
        status="open", created_by=user1.id,
        raid_definition_id=raid_def.id,
    )
    db.session.add(event)
    db.session.commit()

    return {
        "guild": guild,
        "user1": user1, "user2": user2, "user3": user3,
        "char1": char1, "char2": char2, "char3": char3,
        "raid_def": raid_def, "event": event,
    }
