"""Schema, constraint and migration-integrity tests (real PostgreSQL)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import exc, text

from app.models import AuditEvent, ProjectMembership
from tests.conftest import make_project, make_user


def test_unique_membership_per_project_user(db):
    owner = make_user(db, "uniq@example.com")
    project = make_project(db, owner)
    with pytest.raises(exc.IntegrityError):
        db.add(ProjectMembership(project_id=project.id, user_id=owner.id,
                                 role="viewer", membership_status="active"))
        db.commit()
    db.rollback()


def test_invalid_role_rejected(db):
    owner = make_user(db, "role@example.com")
    project = make_project(db, owner)
    with pytest.raises(exc.IntegrityError):
        db.add(ProjectMembership(project_id=project.id, user_id=owner.id,
                                 role="dictator", membership_status="active"))
        db.commit()
    db.rollback()


def test_fk_enforced(db):
    owner = make_user(db, "fk@example.com")
    with pytest.raises(exc.IntegrityError):
        db.add(ProjectMembership(project_id=uuid.uuid4(), user_id=owner.id,
                                 role="viewer", membership_status="active"))
        db.commit()
    db.rollback()


def test_audit_events_are_append_only(db):
    owner = make_user(db, "audit@example.com")
    project = make_project(db, owner)
    event = AuditEvent(project_id=project.id, actor_type="user",
                       actor_id=str(owner.id), action="test.created",
                       entity_type="test", correlation_id=uuid.uuid4())
    db.add(event)
    db.commit()
    db.refresh(event)

    with pytest.raises(exc.DBAPIError):
        db.execute(text("UPDATE audit_events SET action='tampered' WHERE id = :id"), {"id": event.id})
        db.commit()
    db.rollback()

    with pytest.raises(exc.DBAPIError):
        db.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": event.id})
        db.commit()
    db.rollback()
