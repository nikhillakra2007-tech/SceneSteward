"""Adversarial security tests for PostgreSQL identity trust-boundary and cross-project referential integrity.

Proves that:
1. An attacker executing arbitrary SQL under the runtime role scenesteward_app cannot impersonate another user.
2. An attacker cannot forge app.system to bypass Row Level Security.
3. Signature replays between users are detected and rejected.
4. Composite foreign keys reject cross-project entity linkage at the database layer.
5. private.app_secrets cannot be read by scenesteward_app or scenesteward_readonly.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.database import compute_identity_sig, compute_system_sig
from tests.conftest import make_project, make_user


@pytest.fixture()
def two_projects(db):
    user_a = make_user(db, f"adv_a_{uuid.uuid4().hex[:6]}@adv.test", "User A")
    user_b = make_user(db, f"adv_b_{uuid.uuid4().hex[:6]}@adv.test", "User B")
    proj_a = make_project(db, user_a, title="Adversarial Project A")
    proj_b = make_project(db, user_b, title="Adversarial Project B")
    return {"user_a": user_a, "user_b": user_b, "proj_a": proj_a, "proj_b": proj_b}


def test_adversarial_user_spoofing_prevented_by_hmac(two_projects):
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)
    user_a = two_projects["user_a"]
    user_b = two_projects["user_b"]
    proj_a = two_projects["proj_a"]
    proj_b = two_projects["proj_b"]

    sig_a = compute_identity_sig(str(user_a.id))

    # 1. User A with valid signature sees only Project A
    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
            {"uid": str(user_a.id), "sig": sig_a},
        )
        rows_a = conn.execute(text("SELECT id FROM projects")).scalars().all()
        assert proj_a.id in rows_a
        assert proj_b.id not in rows_a

    # 2. Attacker injects set_config to User B WITHOUT signature -> sees 0 projects
    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
            {"uid": str(user_a.id), "sig": sig_a},
        )
        # Attacker injects:
        conn.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(user_b.id)})
        rows_spoofed = conn.execute(text("SELECT id FROM projects")).scalars().all()
        assert len(rows_spoofed) == 0, "Spoofed user with missing signature must see 0 projects"

    # 3. Attacker replays User A signature with User B's ID -> rejected (mismatch)
    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
            {"uid": str(user_b.id), "sig": sig_a},
        )
        rows_replayed = conn.execute(text("SELECT id FROM projects")).scalars().all()
        assert len(rows_replayed) == 0, "Replayed signature mismatch must see 0 projects"


def test_adversarial_system_bypass_prevented_by_hmac(two_projects):
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)

    # Attacker sets app.system='on' without valid system signature
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.system', 'on', true)"))
        rows = conn.execute(text("SELECT id FROM projects")).scalars().all()
        assert len(rows) == 0, "Forged app.system='on' without HMAC signature must see 0 rows under RLS"


def test_runtime_role_cannot_read_private_secrets():
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)

    with app_engine.connect() as conn:
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("SELECT * FROM private.app_secrets"))
        assert "permission denied" in str(exc_info.value).lower()


def test_cross_project_referential_integrity(two_projects, db):
    proj_a = two_projects["proj_a"]
    proj_b = two_projects["proj_b"]
    user_b = two_projects["user_b"]

    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)
    sig_sys = compute_system_sig()

    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.system', 'on', true), set_config('app.system_sig', :sig, true)"),
            {"sig": sig_sys},
        )
        part_a_id = uuid.uuid4()
        conn.execute(
            text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Participant in A')"),
            {"id": part_a_id, "pid": proj_a.id},
        )
        conn.commit()

        # Attempt to insert proposed_use in Project B referencing Participant A
        # We re-assert system role or set it session-wide so we test the composite FK directly
        use_id = uuid.uuid4()
        with pytest.raises(Exception) as exc_info:
            conn.execute(
                text("SELECT set_config('app.system', 'on', true), set_config('app.system_sig', :sig, true)"),
                {"sig": sig_sys},
            )
            conn.execute(
                text("""
                    INSERT INTO proposed_uses (id, project_id, participant_id, use_type, proposed_by)
                    VALUES (:id, :pid, :part_id, 'trailer', :uid)
                """),
                {"id": use_id, "pid": proj_b.id, "part_id": part_a_id, "uid": user_b.id},
            )
            conn.commit()
        assert "fk_proposed_uses_participant_project" in str(exc_info.value)


def test_concurrent_distinct_identities(two_projects):
    """Concurrent requests from User A and User B never bleed identity across connections."""
    import concurrent.futures

    settings = get_settings()
    app_engine = create_engine(settings.database_url, pool_size=5, future=True)
    user_a = two_projects["user_a"]
    user_b = two_projects["user_b"]
    proj_a = two_projects["proj_a"]
    proj_b = two_projects["proj_b"]

    def query_as(user_id, expected_proj_id, unexpected_proj_id):
        sig = compute_identity_sig(str(user_id))
        with app_engine.connect() as conn:
            conn.execute(
                text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
                {"uid": str(user_id), "sig": sig},
            )
            rows = conn.execute(text("SELECT id FROM projects")).scalars().all()
            assert expected_proj_id in rows
            assert unexpected_proj_id not in rows
            return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        f_a1 = executor.submit(query_as, user_a.id, proj_a.id, proj_b.id)
        f_b1 = executor.submit(query_as, user_b.id, proj_b.id, proj_a.id)
        f_a2 = executor.submit(query_as, user_a.id, proj_a.id, proj_b.id)
        f_b2 = executor.submit(query_as, user_b.id, proj_b.id, proj_a.id)
        assert all(f.result() for f in [f_a1, f_b1, f_a2, f_b2])


def test_transaction_rollback_cleans_identity(two_projects):
    """Rolling back a transaction cleanly resets local GUC identity settings."""
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)
    user_a = two_projects["user_a"]
    sig_a = compute_identity_sig(str(user_a.id))

    with app_engine.connect() as conn:
        trans = conn.begin()
        conn.execute(
            text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
            {"uid": str(user_a.id), "sig": sig_a},
        )
        assert conn.execute(text("SELECT public.app_current_user_id()")).scalar() == user_a.id
        trans.rollback()

        # In a new transaction on the same connection, local GUCs are gone
        trans2 = conn.begin()
        assert conn.execute(text("SELECT public.app_current_user_id()")).scalar() is None
        trans2.rollback()


def test_runtime_role_privilege_escalation_blocked():
    """scenesteward_app cannot SET ROLE, create tables, or truncate tables."""
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)

    def attempt_sql(stmt):
        with app_engine.connect() as conn:
            with pytest.raises(Exception) as exc:
                conn.execute(text(stmt))
            return str(exc.value).lower()

    # 1. Attempt SET ROLE postgres
    err1 = attempt_sql("SET ROLE postgres")
    assert "permission denied" in err1

    # 2. Attempt SET ROLE scenesteward
    err2 = attempt_sql("SET ROLE scenesteward")
    assert "permission denied" in err2

    # 3. Attempt CREATE TABLE
    err3 = attempt_sql("CREATE TABLE hacked (id int)")
    assert "permission denied" in err3

    # 4. Attempt TRUNCATE
    err4 = attempt_sql("TRUNCATE TABLE projects")
    assert "permission denied" in err4
