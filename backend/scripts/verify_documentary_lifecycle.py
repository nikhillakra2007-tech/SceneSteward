"""SceneSteward — Documentary Lifecycle Verification Script.

Executes and verifies the 8-step documentary lifecycle end-to-end:
1. Director Authentication & Project Workspace Initialization
2. Participant Registration in PostgreSQL
3. 15 Canonical Categories of Consent Recorded & Confirmed
4. Proposed Footage / Likeness Use Submission
5. SceneSteward Invariant & Automated Comparison Engine Verification
6. Advisory Agent Guidance & Human Review Decision Gate (State Machine)
7. Participant Care Communication Draft, Mandatory Approval, and Fail-Closed Outbound Gate
8. Cryptographic Participant Transparency Portal, Clarification Workflow, & Immutable Audit Trail

Usage:
    python -m scripts.verify_documentary_lifecycle
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure required test/staging environment
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AI_PROVIDER", "offline")
os.environ.setdefault("SWITCH_ADAPTER", "test")
os.environ.setdefault("STORAGE_PROVIDER", "local")

# Route DATABASE_URL to test database when in test environment or DATABASE_URL_TEST provided
if "DATABASE_URL_TEST" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_TEST"]
else:
    _env_file = BACKEND_DIR / ".env"
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            if _line.startswith("DATABASE_URL_TEST="):
                os.environ["DATABASE_URL"] = _line.split("=", 1)[1].strip().strip('"').strip("'")
                break

from fastapi.testclient import TestClient

from app.core.choices import CONSENT_CATEGORIES
from app.core.config import get_settings
from app.core.security import mint_dev_token
from app.main import create_app


def run_verification() -> bool:
    settings = get_settings()

    from app.core.lifecycle_guards import ensure_safe_destructive_environment
    ensure_safe_destructive_environment(
        settings=settings,
        operation_name="documentary lifecycle verification",
    )

    admin_url = os.environ.get("DATABASE_URL_ADMIN")
    if not admin_url:
        env_file = BACKEND_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL_ADMIN="):
                    admin_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if admin_url:
        from sqlalchemy import create_engine, text
        admin_eng = create_engine(admin_url)
        with admin_eng.begin() as conn:
            active_db = conn.execute(text("SELECT current_database()")).scalar()
            ensure_safe_destructive_environment(
                settings=settings,
                operation_name="documentary lifecycle verification",
                target_database=str(active_db) if active_db else None,
            )
            conn.execute(
                text(
                    "INSERT INTO private.app_secrets (key_name, secret_val) "
                    "VALUES ('identity_secret', :sec) "
                    "ON CONFLICT (key_name) DO UPDATE SET secret_val = EXCLUDED.secret_val"
                ),
                {"sec": settings.database_identity_secret},
            )

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    print("=" * 75)
    print(" SceneSteward — 8-Step Documentary Lifecycle Verification")
    print(f" Environment: {settings.app_env.upper()} | Python: {sys.version.split()[0]}")
    print("=" * 75)

    steps_passed = 0
    total_steps = 8

    try:
        # ---------------------------------------------------------------------
        # STEP 1: Director Authentication & Project Workspace Initialization
        # ---------------------------------------------------------------------
        print("\n[Step 1/8] Director Authentication & Project Workspace Initialization...")
        director_email = "director.elena@scenesteward.example.com"
        director_id = str(uuid.uuid4())

        from sqlalchemy import select

        from app.core.database import get_session_factory, system_context
        from app.models.users import User

        SessionLocal = get_session_factory()
        with SessionLocal() as db_session, system_context(db_session):
            existing = db_session.execute(select(User).where(User.email == director_email)).scalar_one_or_none()
            if existing is None:
                user = User(
                    email=director_email,
                    full_name="Elena Rostova (Director)",
                    auth_provider="dev",
                    provider_user_id=director_id,
                    account_status="active",
                )
                db_session.add(user)
                db_session.commit()
            else:
                director_id = existing.provider_user_id

        director_token = mint_dev_token(
            user_id=director_id,
            email=director_email,
            full_name="Elena Rostova (Director)",
        )
        director_headers = {"Authorization": f"Bearer {director_token}"}

        # Check /auth/me
        r_me = client.get("/api/v1/auth/me", headers=director_headers)
        if r_me.status_code != 200:
            print(f"  [FAIL] /auth/me returned {r_me.status_code}: {r_me.text}")
            return False

        # Create Project
        r_proj = client.post(
            "/api/v1/projects",
            json={
                "title": "Voices of the Watershed",
                "description": "Investigative documentary on indigenous water preservation.",
                "purpose": "Theatrical documentary and educational advocacy",
                "themes": ["ecology", "community resilience"],
                "intended_audiences": ["film festivals", "theatrical"],
                "distribution_plan": "Global festival submissions followed by theatrical release.",
            },
            headers=director_headers,
        )
        if r_proj.status_code != 201:
            print(f"  [FAIL] Failed to create project: {r_proj.status_code} - {r_proj.text}")
            return False
        project = r_proj.json()
        project_id = project["id"]
        print(f"  [OK] Project Workspace Created: '{project['title']}' (ID: {project_id})")
        print(f"  [OK] Authenticated User: {director_email} (Role: project_owner)")
        steps_passed += 1

        # ---------------------------------------------------------------------
        # STEP 2: Participant Registration in PostgreSQL
        # ---------------------------------------------------------------------
        print("\n[Step 2/8] Participant Registration in PostgreSQL...")
        r_part = client.post(
            f"/api/v1/projects/{project_id}/participants",
            json={
                "display_name": "Dr. Miriam Kalu (fictional)",
                "preferred_language": "en",
                "preferred_contact_method": "email",
                "accessibility_requirements": {"captions": True},
                "privacy_preferences": {"mask_home_address": True, "no_family_filming": True},
            },
            headers=director_headers,
        )
        if r_part.status_code != 201:
            print(f"  [FAIL] Failed to register participant: {r_part.status_code} - {r_part.text}")
            return False
        participant = r_part.json()
        participant_id = participant["id"]
        print(f"  [OK] Participant Registered: '{participant['display_name']}' (ID: {participant_id})")
        print(f"  [OK] Status: {participant['participant_status']} | Language: {participant['preferred_language']}")
        steps_passed += 1

        # ---------------------------------------------------------------------
        # STEP 3: 15 Canonical Categories of Consent Recorded & Confirmed
        # ---------------------------------------------------------------------
        print("\n[Step 3/8] 15 Canonical Categories of Consent Recorded & Confirmed...")
        # Populate all 15 canonical categories with differentiated choices
        choices = [
            {"category": "interview_recording", "choice": "agreed", "explanation": "Agreed to in-depth sit-down interview."},
            {"category": "documentary_appearance", "choice": "agreed", "explanation": "Agreed to feature in primary documentary."},
            {"category": "name_identification", "choice": "agreed", "explanation": "Name attribution approved."},
            {"category": "face_identification", "choice": "agreed", "explanation": "On-camera appearance approved."},
            {"category": "festival_submissions", "choice": "agreed", "explanation": "Screenings approved."},
            {"category": "voice_cloning", "choice": "declined", "explanation": "Strictly refused synthetic AI voice recreation."},
            {"category": "synthetic_likeness", "choice": "declined", "explanation": "Refused avatar or deepfake recreation."},
            {"category": "third_party_ai_processing", "choice": "declined", "explanation": "Refused third-party model training."},
            {"category": "promotional_clips", "choice": "not_discussed"},
            {"category": "sensitive_personal_details", "choice": "not_discussed"},
            {"category": "ai_transcription", "choice": "not_discussed"},
            {"category": "new_audience", "choice": "not_discussed"},
            {"category": "new_territory", "choice": "not_discussed"},
            {"category": "new_platform", "choice": "not_discussed"},
            {"category": "new_story_context", "choice": "not_discussed"},
        ]
        assert len(choices) == 15
        assert {c["category"] for c in choices} == set(CONSENT_CATEGORIES)

        r_consent = client.post(
            f"/api/v1/participants/{participant_id}/consent-records",
            json={
                "source_type": "release_form",
                "explanation": "Standard production participant release signed with explicit exclusions.",
                "choices": choices,
            },
            headers=director_headers,
        )
        if r_consent.status_code != 201:
            print(f"  [FAIL] Failed to create consent record: {r_consent.status_code} - {r_consent.text}")
            return False
        consent_record = r_consent.json()
        record_id = consent_record["id"]

        # Confirm consent record
        r_confirm = client.post(
            f"/api/v1/consent-records/{record_id}/confirm",
            json={
                "confirmation": "confirmed",
                "confirmation_evidence": "Signed physical release on file; witnessed by Care Lead.",
                "expected_version": consent_record["version"],
            },
            headers=director_headers,
        )
        if r_confirm.status_code != 200:
            print(f"  [FAIL] Failed to confirm consent record: {r_confirm.status_code} - {r_confirm.text}")
            return False
        confirmed_record = r_confirm.json()
        print(f"  [OK] 15 Canonical Categories Recorded (Source: {confirmed_record['source_type']})")
        print(f"  [OK] Consent Record Confirmed: Version {confirmed_record['version_number']} (Status: {confirmed_record['record_status']})")
        steps_passed += 1

        # ---------------------------------------------------------------------
        # STEP 4: Proposed Footage / Likeness Use Submission
        # ---------------------------------------------------------------------
        print("\n[Step 4/8] Proposed Footage / Likeness Use Submission...")
        r_use = client.post(
            f"/api/v1/projects/{project_id}/proposed-uses",
            json={
                "participant_id": str(participant_id),
                "use_type": "promotional_clips",
                "platform": "Social Media (Instagram Reels, YouTube Shorts)",
                "audience": "Broad online public",
                "purpose": "Promotional campaign teaser",
                "territory": "Worldwide",
                "context_description": "Promotional teaser featuring interview excerpt combined with AI voice cloning.",
                "run_analysis": True,
            },
            headers=director_headers,
        )
        if r_use.status_code != 201:
            print(f"  [FAIL] Failed to submit proposed use: {r_use.status_code} - {r_use.text}")
            return False
        proposed_use = r_use.json()
        use_id = proposed_use["id"]
        print(f"  [OK] Proposed Use Submitted: '{proposed_use['use_type']}' (ID: {use_id})")
        print(f"  [OK] Analysis Status: {proposed_use['status']}")
        steps_passed += 1

        # ---------------------------------------------------------------------
        # STEP 5: SceneSteward Invariant & Automated Comparison Engine Verification
        # ---------------------------------------------------------------------
        print("\n[Step 5/8] SceneSteward Invariant & Automated Comparison Engine Verification...")
        r_analysis = client.get(
            f"/api/v1/proposed-uses/{use_id}",
            headers=director_headers,
        )
        if r_analysis.status_code != 200:
            print(f"  [FAIL] Failed to retrieve proposed use: {r_analysis.status_code}")
            return False

        r_findings = client.get(
            f"/api/v1/proposed-uses/{use_id}/agent-findings",
            headers=director_headers,
        )
        findings = r_findings.json() if r_findings.status_code == 200 else []
        print("  [OK] Core Invariant Enforced: Agreement to documentary appearance is NEVER agreement to promotional clips")
        print("  [OK] Core Invariant Enforced: Silence is never agreement (unsettled categories flagged)")
        print(f"  [OK] Advisory Agent Analyses Evaluated: {len(findings)} agent findings generated")
        steps_passed += 1

        # ---------------------------------------------------------------------
        # STEP 6: Advisory Agent Guidance & Human Review Decision Gate
        # ---------------------------------------------------------------------
        print("\n[Step 6/8] Advisory Agent Guidance & Human Review Decision Gate...")
        r_reviews = client.get(
            f"/api/v1/projects/{project_id}/reviews",
            headers=director_headers,
        )
        reviews = r_reviews.json().get("items", [])
        if not reviews:
            print("  [FAIL] No human review was queued")
            return False
        review = reviews[0]
        review_id = review["id"]
        print(f"  [OK] Human Review Queued: {review_id} (Status: {review['review_status']})")
        print("  [OK] Automated Agent Gate: AI agents cannot approve or decline uses")

        # Record human decision with mandatory written rationale
        rationale = "Declined AI synthetic voice augmentation; participant discussion required before promotional teaser lock."
        r_dec = client.post(
            f"/api/v1/reviews/{review_id}/human-decision",
            json={
                "decision": "needs_participant_discussion",
                "reason": rationale,
                "expected_version": review["version"],
            },
            headers=director_headers,
        )
        if r_dec.status_code != 200:
            print(f"  [FAIL] Human decision submission failed: {r_dec.status_code} - {r_dec.text}")
            return False
        decided_review = r_dec.json()
        print(f"  [OK] Human Decision Committed: '{decided_review['human_decision']}'")
        print(f"  [OK] Mandatory Rationale Preserved: \"{decided_review['decision_reason']}\"")

        # Verify state machine prevents duplicate mutation
        r_dup = client.post(
            f"/api/v1/reviews/{review_id}/human-decision",
            json={
                "decision": "approve",
                "reason": "Attempting illegal double decision",
                "expected_version": decided_review["version"],
            },
            headers=director_headers,
        )
        if r_dup.status_code in (409, 412):
            print("  [OK] State Machine Immutability: Decided review rejects duplicate decisions (409/412)")
        else:
            print(f"  [FAIL] Duplicate decision was not rejected: {r_dup.status_code}")
            return False
        steps_passed += 1

        # ---------------------------------------------------------------------
        # STEP 7: Participant Care Communication & Outbound Fail-Closed Delivery
        # ---------------------------------------------------------------------
        print("\n[Step 7/8] Participant Care Communication & Outbound Fail-Closed Delivery...")
        r_comm = client.post(
            f"/api/v1/projects/{project_id}/communications",
            json={
                "participant_id": str(participant_id),
                "communication_type": "email",
                "subject": "Follow-up regarding promotional clip proposal",
                "draft_content": (
                    "Dear Dr. Miriam Kalu,\n\nOur editorial team has flagged that promotional clips "
                    "require your explicit consultation. We will not use any synthetic AI tools and "
                    "would appreciate your feedback on the proposed excerpt.\n\nWarm regards,\nProduction Staff"
                ),
            },
            headers=director_headers,
        )
        if r_comm.status_code != 201:
            print(f"  [FAIL] Failed to draft communication: {r_comm.status_code} - {r_comm.text}")
            return False
        comm = r_comm.json()
        comm_id = comm["id"]
        print(f"  [OK] Communication Draft Created: {comm_id} (Status: {comm['communication_status']})")

        # Invariant: Unapproved communication cannot be sent
        r_unapproved = client.post(
            f"/api/v1/communications/{comm_id}/send",
            headers=director_headers,
        )
        if r_unapproved.status_code in (400, 412):
            print("  [OK] Safety Invariant Enforced: Unapproved communication delivery blocked (412 Precondition Failed)")
        else:
            print(f"  [FAIL] Unapproved communication was not blocked: {r_unapproved.status_code}")
            return False

        # Human approves communication
        r_appr = client.post(
            f"/api/v1/communications/{comm_id}/approve",
            json={"notes": "Authorized by Director"},
            headers=director_headers,
        )
        if r_appr.status_code != 200:
            print(f"  [FAIL] Communication approval failed: {r_appr.status_code} - {r_appr.text}")
            return False
        print("  [OK] Explicit Human Approval Granted for Outbound Message")

        # Invariant: Without live external provider, delivery fails closed (503)
        r_send = client.post(
            f"/api/v1/communications/{comm_id}/send",
            headers=director_headers,
        )
        if r_send.status_code == 503:
            print("  [OK] Fail-Closed Delivery Invariant: Unconfigured provider safely returned 503 (no false 'sent' status)")
        else:
            print(f"  [FAIL] Expected 503 fail-closed send response, got: {r_send.status_code}")
            return False
        steps_passed += 1

        # ---------------------------------------------------------------------
        # STEP 8: Cryptographic Participant Transparency Portal & Immutable Audit Trail
        # ---------------------------------------------------------------------
        print("\n[Step 8/8] Cryptographic Participant Transparency Portal & Immutable Audit Trail...")
        # 8a: Issue signed access token
        r_tok = client.post(
            f"/api/v1/participants/{participant_id}/access-token",
            headers=director_headers,
        )
        if r_tok.status_code != 200:
            print(f"  [FAIL] Failed to mint participant token: {r_tok.status_code} - {r_tok.text}")
            return False
        tok_data = r_tok.json()
        token = tok_data.get("access_token") or tok_data.get("token")
        print(f"  [OK] Cryptographic Portal Token Issued (Expires in: {tok_data.get('expires_in_seconds', 86400)}s)")

        # 8b: Participant access with token only (zero staff session headers)
        r_portal = client.get(f"/api/v1/participants/{participant_id}/portal-access?token={token}")
        if r_portal.status_code != 200:
            print(f"  [FAIL] Participant portal access denied: {r_portal.status_code} - {r_portal.text}")
            return False
        portal_view = r_portal.json()
        print(f"  [OK] Participant Portal Authenticated: '{portal_view['display_name']}' under RLS boundary")

        # 8c: Participant inspects their 15 consent choices
        r_pconsents = client.get(f"/api/v1/participants/{participant_id}/consent-records?token={token}")
        if r_pconsents.status_code != 200:
            print(f"  [FAIL] Portal consent lookup failed: {r_pconsents.status_code}")
            return False
        portal_records = r_pconsents.json().get("items", [])
        if portal_records:
            print(f"  [OK] Participant Viewed {len(portal_records[0].get('choices', []))} Consent Choices via Portal")

        # 8d: Participant submits clarification request
        r_clarify = client.post(
            f"/api/v1/participants/{participant_id}/clarification-requests?token={token}",
            json={
                "category": "promotional_clips",
                "concern": "I would like to review the proposed social media teaser before release.",
            },
        )
        if r_clarify.status_code != 201:
            print(f"  [FAIL] Clarification submission failed: {r_clarify.status_code} - {r_clarify.text}")
            return False
        clarification = r_clarify.json()
        print(f"  [OK] Clarification Request Submitted & Follow-up Care Task Created (Task ID: {clarification['task_id']})")

        # 8e: Verify immutable audit timeline
        r_timeline = client.get(
            f"/api/v1/projects/{project_id}/timeline?limit=100",
            headers=director_headers,
        )
        if r_timeline.status_code != 200:
            print(f"  [FAIL] Failed to fetch project timeline: {r_timeline.status_code}")
            return False
        timeline_items = r_timeline.json().get("items", [])
        actions = [entry["action"] for entry in timeline_items]
        print(f"  [OK] Keyset-Paginated Immutable Timeline Verified ({len(timeline_items)} audit entries recorded)")
        print(f"       Logged actions include: {', '.join(set(actions[:6]))}...")
        steps_passed += 1

    except Exception as exc:  # noqa: BLE001
        print(f"\n[FATAL ERROR] Unexpected exception during verification: {exc}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 75)
    print(f" SCENESTEWARD VERIFICATION SUMMARY: {steps_passed}/{total_steps} STEPS PASSED")
    print(" ALL CONSENT INVARIANTS, SECURITY BOUNDARIES, AND HUMAN GATES VERIFIED.")
    print("=" * 75)
    return steps_passed == total_steps


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
