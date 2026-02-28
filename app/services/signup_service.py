"""Signup service with auto-bench logic."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.enums import SignupStatus
from app.extensions import db
from app.models.signup import Signup


def _count_going(raid_event_id: int) -> int:
    """Return the number of going signups for an event."""
    return db.session.execute(
        sa.select(sa.func.count(Signup.id)).where(
            Signup.raid_event_id == raid_event_id,
            Signup.status == SignupStatus.GOING.value,
        )
    ).scalar_one()


def _auto_promote_bench(raid_event_id: int, role: str) -> None:
    """Promote the first matching benched signup to 'going'.

    Preference order: mains before alts, then earliest created_at.
    """
    from app.models.character import Character

    # Find benched signups for this role, prefer mains, then oldest
    benched = db.session.execute(
        sa.select(Signup)
        .join(Character, Character.id == Signup.character_id)
        .where(
            Signup.raid_event_id == raid_event_id,
            Signup.chosen_role == role,
            Signup.status == SignupStatus.BENCH.value,
        )
        .order_by(Character.is_main.desc(), Signup.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()

    if benched is not None:
        benched.status = SignupStatus.GOING.value
        db.session.commit()


def create_signup(
    raid_event_id: int,
    user_id: int,
    character_id: int,
    chosen_role: str,
    chosen_spec: Optional[str],
    note: Optional[str],
    raid_size: int,
) -> Signup:
    """Create a signup, applying auto-bench if the roster is full."""
    going_count = _count_going(raid_event_id)
    status = (
        SignupStatus.BENCH.value if going_count >= raid_size else SignupStatus.GOING.value
    )

    signup = Signup(
        raid_event_id=raid_event_id,
        user_id=user_id,
        character_id=character_id,
        chosen_role=chosen_role,
        chosen_spec=chosen_spec,
        status=status,
        note=note,
    )
    db.session.add(signup)
    db.session.commit()
    return signup


def get_signup(signup_id: int) -> Optional[Signup]:
    return db.session.get(Signup, signup_id)


def update_signup(signup: Signup, data: dict) -> Signup:
    """Update a signup. Auto-promotes a benched player when a 'going' player
    changes to a non-going status (declined, bench, tentative, etc.)."""
    old_status = signup.status
    old_role = signup.chosen_role

    allowed = {"chosen_spec", "chosen_role", "status", "note"}
    for key, value in data.items():
        if key in allowed:
            setattr(signup, key, value)
    db.session.commit()

    # If the player was going and is no longer going, auto-promote from bench
    new_status = signup.status
    if old_status == SignupStatus.GOING.value and new_status != SignupStatus.GOING.value:
        _auto_promote_bench(signup.raid_event_id, old_role)

    return signup


def delete_signup(signup: Signup) -> None:
    """Delete a signup and auto-promote a benched player if applicable."""
    role = signup.chosen_role
    raid_event_id = signup.raid_event_id
    was_going = signup.status == SignupStatus.GOING.value

    db.session.delete(signup)
    db.session.commit()

    if was_going:
        _auto_promote_bench(raid_event_id, role)


def decline_signup(signup: Signup) -> Signup:
    """Decline a signup and auto-promote a benched player if applicable."""
    role = signup.chosen_role
    raid_event_id = signup.raid_event_id
    was_going = signup.status == SignupStatus.GOING.value

    signup.status = SignupStatus.DECLINED.value
    db.session.commit()

    if was_going:
        _auto_promote_bench(raid_event_id, role)

    return signup


def list_signups(raid_event_id: int) -> list[Signup]:
    return list(
        db.session.execute(
            sa.select(Signup)
            .where(Signup.raid_event_id == raid_event_id)
            .options(sa.orm.joinedload(Signup.character))
        ).scalars().unique().all()
    )
