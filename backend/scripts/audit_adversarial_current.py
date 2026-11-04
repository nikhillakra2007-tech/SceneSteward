"""Adversarial security audit: test trust-boundary of app.user_id and app.system
under the real restricted runtime role scenesteward_app.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def run_adversarial_audit():
    settings = get_settings()
    # Connect as admin to set up test projects and users
    admin_engine = create_engine(settings.migration_database_url or settings.database_url, future=True)
    # Connect as runtime role
    app_engine = create_engine(settings.database_url, future=True)

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    proj_a_id = uuid.uuid4()
    proj_b_id = uuid.uuid4()

    print("[1] Provisioning test users and projects...")
    with admin_engine.connect() as conn:
        conn.execute(text("INSERT INTO users (id, email, full_name, auth_provider, provider_user_id, account_status) VALUES (:id, :e, :n, 'dev', :puid, 'active')"),
                     [{"id": user_a_id, "e": f"a_{user_a_id.hex[:8]}@test.com", "n": "User A", "puid": str(user_a_id)},
                      {"id": user_b_id, "e": f"b_{user_b_id.hex[:8]}@test.com", "n": "User B", "puid": str(user_b_id)}])
        conn.execute(text("INSERT INTO projects (id, title, purpose, created_by) VALUES (:id, :t, :p, :cb)"),
                     [{"id": proj_a_id, "t": "Project A", "p": "Purpose A", "cb": user_a_id},
                      {"id": proj_b_id, "t": "Project B", "p": "Purpose B", "cb": user_b_id}])
        conn.execute(text("INSERT INTO project_memberships (project_id, user_id, role, membership_status, invited_by) VALUES (:pid, :uid, 'project_owner', 'active', :uid)"),
                     [{"pid": proj_a_id, "uid": user_a_id},
                      {"pid": proj_b_id, "uid": user_b_id}])
        conn.commit()

    print("\n[2] Executing Adversarial Tests under scenesteward_app (NOBYPASSRLS)...")

    from app.core.database import compute_identity_sig, compute_system_sig

    sig_a = compute_identity_sig(str(user_a_id))
    sig_sys = compute_system_sig()

    # Test 1: User A legitimate signed access
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
                     {"uid": str(user_a_id), "sig": sig_a})
        rows_a = conn.execute(text("SELECT id, title FROM projects")).fetchall()
        print(f"  Test 1 (Legitimate User A with signature): sees {len(rows_a)} project(s): {[r[1] for r in rows_a]}")
        assert len(rows_a) == 1 and rows_a[0][0] == proj_a_id, "User A should see Project A"

    # Test 2: Attacker has User A connection, injects raw SQL without signature to impersonate User B
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
                     {"uid": str(user_a_id), "sig": sig_a})
        # Injected SQL without signature:
        conn.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(user_b_id)})
        rows_spoofed = conn.execute(text("SELECT id, title FROM projects")).fetchall()
        print(f"  Test 2 (Spoofed User B SELECT, no sig): sees {len(rows_spoofed)} project(s): {[r[1] for r in rows_spoofed]}")
        assert len(rows_spoofed) == 0, "Spoofed user with no signature must see 0 projects"

    # Test 3: Attacker attempts to replay User A signature with User B ID
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
                     {"uid": str(user_b_id), "sig": sig_a})
        rows_replayed = conn.execute(text("SELECT id, title FROM projects")).fetchall()
        print(f"  Test 3 (Replayed Sig mismatch SELECT): sees {len(rows_replayed)} project(s): {[r[1] for r in rows_replayed]}")
        assert len(rows_replayed) == 0, "Replayed signature mismatch must see 0 projects"

    # Test 4: Attacker attempts cross-project INSERT into Project B
    with app_engine.connect() as conn:
        # Injected SQL attempting to insert into Project B while pretending to be User B without valid sig
        conn.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(user_b_id)})
        part_id = uuid.uuid4()
        try:
            conn.execute(text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Injected')"),
                         {"id": part_id, "pid": proj_b_id})
            conn.commit()
            print("  Test 4 (Spoofed User B INSERT): Successfully inserted participant into Project B! (VULNERABLE)")
        except Exception as e:  # noqa: BLE001
            print("  Test 4 (Spoofed User B INSERT): Successfully BLOCKED by PostgreSQL RLS:", type(e).__name__)

    # Test 5: Attacker attempts cross-project UPDATE on Project B
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(user_b_id)})
        res = conn.execute(text("UPDATE projects SET title = 'Hacked' WHERE id = :pid"), {"pid": proj_b_id})
        conn.commit()
        print(f"  Test 5 (Spoofed User B UPDATE): updated {res.rowcount} row(s) (Expected 0)")
        assert res.rowcount == 0

    # Test 6: Attacker attempts cross-project DELETE on Project B
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(user_b_id)})
        res = conn.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": proj_b_id})
        conn.commit()
        print(f"  Test 6 (Spoofed User B DELETE): deleted {res.rowcount} row(s) (Expected 0)")
        assert res.rowcount == 0

    # Test 7: Attacker attempts to forge app.system='on' without signature
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.system', 'on', true)"))
        all_projects = conn.execute(text("SELECT id, title FROM projects")).fetchall()
        print(f"  Test 7 (Forged app.system='on', no sig): sees {len(all_projects)} project(s) (Expected 0)")
        assert len(all_projects) == 0

    # Test 8: Attacker attempts to read private.app_secrets directly
    with app_engine.connect() as conn:
        try:
            conn.execute(text("SELECT * FROM private.app_secrets"))
            print("  Test 8 (Read private.app_secrets): SUCCEEDED! (VULNERABLE)")
        except Exception as e:  # noqa: BLE001
            print("  Test 8 (Read private.app_secrets): Successfully BLOCKED by PostgreSQL permissions:", type(e).__name__)

    # Test 9: Legitimate System Context with signature
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.system', 'on', true), set_config('app.system_sig', :sig, true)"),
                     {"sig": sig_sys})
        all_sys_projects = conn.execute(text("SELECT id, title FROM projects")).fetchall()
        print(f"  Test 9 (Legitimate System Context with sig): sees {len(all_sys_projects)} project(s)")
        assert len(all_sys_projects) >= 2

    # Test 10: Cross-project referential integrity: Try to attach Participant from Project A to Proposed Use in Project B
    with app_engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.system', 'on', true), set_config('app.system_sig', :sig, true)"),
                     {"sig": sig_sys})
        part_a_id = uuid.uuid4()
        conn.execute(text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Part A')"),
                     {"id": part_a_id, "pid": proj_a_id})
        conn.commit()
        
        # Now try to insert proposed use with project_id = Project B, but participant_id = Part A
        use_id = uuid.uuid4()
        try:
            conn.execute(text("""
                INSERT INTO proposed_uses (id, project_id, participant_id, use_type, proposed_by)
                VALUES (:id, :pid, :part_id, 'trailer', :uid)
            """), {"id": use_id, "pid": proj_b_id, "part_id": part_a_id, "uid": user_b_id})
            conn.commit()
            print("  Test 10 (Cross-project FK mismatch): SUCCEEDED! (VULNERABLE)")
        except Exception as e:  # noqa: BLE001
            print("  Test 10 (Cross-project FK mismatch): Successfully REJECTED by composite foreign key:", type(e).__name__)

    # Cleanup test data
    with admin_engine.connect() as conn:
        conn.execute(text("DELETE FROM participants WHERE id = :id"), {"id": part_id})
        conn.execute(text("DELETE FROM project_memberships WHERE project_id IN (:pa, :pb)"), {"pa": proj_a_id, "pb": proj_b_id})
        conn.execute(text("DELETE FROM projects WHERE id IN (:pa, :pb)"), {"pa": proj_a_id, "pb": proj_b_id})
        conn.execute(text("DELETE FROM users WHERE id IN (:ua, :ub)"), {"ua": user_a_id, "ub": user_b_id})
        conn.commit()

if __name__ == "__main__":
    run_adversarial_audit()
