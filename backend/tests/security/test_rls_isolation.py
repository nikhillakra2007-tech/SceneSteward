"""Direct-SQL row-level security (RLS) isolation & policy tests.

These tests execute queries directly through the runtime database role
`scenesteward_app` (NON-owner role, NOBYPASSRLS) to prove that isolation
is enforced at the PostgreSQL engine level, not merely in application route logic.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.database import clear_identity, get_session_factory, set_identity
from tests.conftest import make_user


@pytest.fixture()
def rls_session():
    """A session connected as scenesteward_app (RLS strictly enforced)."""
    session = get_session_factory()()
    clear_identity(session)
    try:
        yield session
    finally:
        clear_identity(session)
        session.close()


def test_deny_by_default_without_identity(rls_session, db):
    """A connection with no app.user_id set sees zero rows on protected tables."""
    owner = make_user(db, "owner1@rls.test")
    p_id = uuid.uuid4()
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Secret P1', 'active', :u, 1)"),
               {"id": p_id, "u": owner.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": p_id, "u": owner.id})
    db.commit()

    # Query using runtime role with no identity set
    rows = rls_session.execute(text("SELECT id, title FROM projects")).fetchall()
    assert len(rows) == 0, f"Expected 0 rows without identity, got {rows}"


def test_cross_project_select_isolation(rls_session, db):
    """User A cannot SELECT projects or participants belonging to Project B."""
    user_a = make_user(db, "alice@rls.test")
    user_b = make_user(db, "bob@rls.test")

    proj_a_id = uuid.uuid4()
    proj_b_id = uuid.uuid4()
    part_a_id = uuid.uuid4()
    part_b_id = uuid.uuid4()

    # Project A
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Project A', 'active', :u, 1)"),
               {"id": proj_a_id, "u": user_a.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_a_id, "u": user_a.id})
    db.execute(text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :p, 'Participant A')"),
               {"id": part_a_id, "p": proj_a_id})

    # Project B
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Project B', 'active', :u, 1)"),
               {"id": proj_b_id, "u": user_b.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_b_id, "u": user_b.id})
    db.execute(text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :p, 'Participant B')"),
               {"id": part_b_id, "p": proj_b_id})
    db.commit()

    # Set identity as User A
    set_identity(user_a.id, rls_session)
    projects = rls_session.execute(text("SELECT id FROM projects")).scalars().all()
    assert proj_a_id in projects
    assert proj_b_id not in projects

    participants = rls_session.execute(text("SELECT id FROM participants")).scalars().all()
    assert part_a_id in participants
    assert part_b_id not in participants

    # Switch identity to User B
    set_identity(user_b.id, rls_session)
    rls_session.commit()  # fresh transaction
    projects_b = rls_session.execute(text("SELECT id FROM projects")).scalars().all()
    assert proj_b_id in projects_b
    assert proj_a_id not in projects_b


def test_cross_project_insert_denied(rls_session, db):
    """User A cannot INSERT a participant into Project B."""
    user_a = make_user(db, "alice_insert@rls.test")
    user_b = make_user(db, "bob_insert@rls.test")

    proj_b_id = uuid.uuid4()
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Project B', 'active', :u, 1)"),
               {"id": proj_b_id, "u": user_b.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_b_id, "u": user_b.id})
    db.commit()

    set_identity(user_a.id, rls_session)
    with pytest.raises(ProgrammingError) as exc_info:
        rls_session.execute(
            text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :p, 'Illegal')"),
            {"id": uuid.uuid4(), "p": proj_b_id},
        )
    assert "violates row-level security policy" in str(exc_info.value)
    rls_session.rollback()


def test_cross_project_update_invisible_or_denied(rls_session, db):
    """User A cannot UPDATE Project B."""
    user_a = make_user(db, "alice_upd@rls.test")
    user_b = make_user(db, "bob_upd@rls.test")

    proj_b_id = uuid.uuid4()
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Project B', 'active', :u, 1)"),
               {"id": proj_b_id, "u": user_b.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_b_id, "u": user_b.id})
    db.commit()

    set_identity(user_a.id, rls_session)
    res = rls_session.execute(
        text("UPDATE projects SET title = 'Hacked' WHERE id = :id"),
        {"id": proj_b_id},
    )
    # Under RLS, updating a row that User A cannot see affects 0 rows
    assert res.rowcount == 0
    rls_session.commit()

    # Verify Project B title remained untouched
    title = db.execute(text("SELECT title FROM projects WHERE id = :id"), {"id": proj_b_id}).scalar()
    assert title == "Project B"


def test_cross_project_delete_invisible_or_denied(rls_session, db):
    """User A cannot DELETE records from Project B."""
    user_a = make_user(db, "alice_del@rls.test")
    user_b = make_user(db, "bob_del@rls.test")

    proj_b_id = uuid.uuid4()
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Project B', 'active', :u, 1)"),
               {"id": proj_b_id, "u": user_b.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_b_id, "u": user_b.id})
    db.commit()

    set_identity(user_a.id, rls_session)
    res = rls_session.execute(
        text("DELETE FROM projects WHERE id = :id"),
        {"id": proj_b_id},
    )
    assert res.rowcount == 0
    rls_session.commit()

    exists = db.execute(text("SELECT 1 FROM projects WHERE id = :id"), {"id": proj_b_id}).scalar()
    assert exists == 1


def test_contact_records_role_restriction(rls_session, db):
    """Editor in Project A cannot SELECT participant_contact_records; Care Lead can."""
    owner = make_user(db, "owner_contact@rls.test")
    editor = make_user(db, "editor_contact@rls.test")
    care_lead = make_user(db, "care_contact@rls.test")

    proj_id = uuid.uuid4()
    part_id = uuid.uuid4()
    contact_id = uuid.uuid4()

    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Project C', 'active', :u, 1)"),
               {"id": proj_id, "u": owner.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_id, "u": owner.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'editor', 'active')"),
               {"p": proj_id, "u": editor.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'participant_care_lead', 'active')"),
               {"p": proj_id, "u": care_lead.id})
    db.execute(text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :p, 'Participant C')"),
               {"id": part_id, "p": proj_id})
    db.execute(text("INSERT INTO participant_contact_records (id, participant_id, contact_type, encrypted_contact_data) VALUES (:id, :p, 'email', 'encrypted_data')"),
               {"id": contact_id, "p": part_id})
    db.commit()

    # Editor attempts direct SELECT
    set_identity(editor.id, rls_session)
    editor_rows = rls_session.execute(text("SELECT id FROM participant_contact_records")).fetchall()
    assert len(editor_rows) == 0

    # Care Lead attempts direct SELECT
    set_identity(care_lead.id, rls_session)
    rls_session.commit()
    care_rows = rls_session.execute(text("SELECT id FROM participant_contact_records")).fetchall()
    assert len(care_rows) == 1
    assert care_rows[0][0] == contact_id


def test_connection_pool_context_isolation(rls_session, db):
    """When a transaction finishes and context is cleared, no residual identity leaks."""
    user = make_user(db, "pool_user@rls.test")
    proj_id = uuid.uuid4()
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Pool Proj', 'active', :u, 1)"),
               {"id": proj_id, "u": user.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_id, "u": user.id})
    db.commit()

    set_identity(user.id, rls_session)
    assert len(rls_session.execute(text("SELECT id FROM projects")).fetchall()) == 1

    # Now clear identity and commit
    clear_identity(rls_session)
    rls_session.commit()

    # In next transaction, setting must be NULL
    val = rls_session.execute(text("SELECT current_setting('app.user_id', true)")).scalar()
    assert val is None or val == ""
    # And zero rows visible
    assert len(rls_session.execute(text("SELECT id FROM projects")).fetchall()) == 0


def test_audit_events_immutability(rls_session, db):
    """Audit events cannot be modified or deleted by runtime role (RLS) or owner role (triggers)."""
    user = make_user(db, "audit_imm@rls.test")
    proj_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    db.execute(text("INSERT INTO projects (id, title, status, created_by, version) VALUES (:id, 'Audit Proj', 'active', :u, 1)"),
               {"id": proj_id, "u": user.id})
    db.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status) VALUES (:p, :u, 'project_owner', 'active')"),
               {"p": proj_id, "u": user.id})
    db.execute(text("INSERT INTO audit_events (id, project_id, actor_type, actor_id, action, entity_type, entity_id, new_value) VALUES (:id, :p, 'user', :u, 'project.created', 'project', :p, '{\"title\":\"Audit Proj\"}')"),
               {"id": audit_id, "p": proj_id, "u": str(user.id)})
    db.commit()

    # Layer 1: scenesteward_app has no UPDATE or DELETE policy -> 0 rows affected
    set_identity(user.id, rls_session)
    res_upd = rls_session.execute(text("UPDATE audit_events SET action = 'tampered' WHERE id = :id"), {"id": audit_id})
    assert res_upd.rowcount == 0
    res_del = rls_session.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": audit_id})
    assert res_del.rowcount == 0
    rls_session.commit()

    # Layer 2: Even table owner (which bypasses RLS) is blocked by the database integrity trigger
    with pytest.raises(ProgrammingError) as exc_info:
        db.execute(text("UPDATE audit_events SET action = 'tampered' WHERE id = :id"), {"id": audit_id})
    assert "audit_events is append-only" in str(exc_info.value)
    db.rollback()

    with pytest.raises(ProgrammingError) as exc_info:
        db.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": audit_id})
    assert "audit_events is append-only" in str(exc_info.value)
    db.rollback()
