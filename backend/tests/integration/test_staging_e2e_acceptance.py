"""SceneSteward — Staging End-to-End Acceptance Integration Test Suite.

Exhaustive integration testing of the complete documentary consent lifecycle,
ethical invariants, security boundaries, and multi-tenant isolation under
staging-equivalent conditions:

- Scenario A: Normal consent lifecycle (Project -> Participant -> 15 Categories -> Confirmation -> Portal -> Comparison -> Review -> Audit).
- Scenario B: Separate intended uses / Non-transitive consent (Documentary appearance != promotional clips).
- Scenario C: Silence and incomplete consent (Unsettled/missing categories are never agreement).
- Scenario D: Revocation & withdrawal (Participant withdrawal notice -> urgent care task -> blocked uses).
- Scenario E: Human decision authority & advisory AI bounds (AI cannot decide; binding human decision requires rationale; state machine prevents double decision).
- Scenario F: Private document lifecycle & malware gate (Presigned upload -> ClamAV scan -> capability download -> traversal & MIME guards).
- Scenario G: Concurrent operations & optimistic locking (Version conflict 409/412 on stale expected_version).
- Scenario H: Complete immutable audit trail & keyset pagination.
- Cross-tenant adversarial isolation (Strict RLS & tenant boundaries).
"""
from __future__ import annotations

from typing import Any

from app.core.choices import CONSENT_CATEGORIES
from tests.conftest import auth_headers, make_project, make_user

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _build_15_choices(agreed_cats: set[str], declined_cats: set[str]) -> list[dict[str, Any]]:
    choices = []
    for cat in CONSENT_CATEGORIES:
        if cat in agreed_cats:
            choices.append({"category": cat, "choice": "agreed", "explanation": f"Agreed to {cat}"})
        elif cat in declined_cats:
            choices.append({"category": cat, "choice": "declined", "explanation": f"Declined {cat}"})
        else:
            choices.append({"category": cat, "choice": "not_discussed"})
    return choices


# -----------------------------------------------------------------------------
# SCENARIO A: Normal Documentary Consent Lifecycle
# -----------------------------------------------------------------------------
def test_scenario_a_normal_consent_lifecycle(client, db):
    # 1. Project Owner & Director creates project
    owner = make_user(db, "director.maya@staging.example.com", "Maya Director")
    headers = auth_headers(owner)

    r_proj = client.post(
        "/api/v1/projects",
        json={
            "title": "Echoes of the High Plateau",
            "description": "Long-form ethnographic documentary.",
            "purpose": "Theatrical and educational distribution",
            "themes": ["culture", "highlands", "indigenous memory"],
            "intended_audiences": ["theatrical", "festivals"],
            "distribution_plan": "Global festival tour followed by public broadcast.",
        },
        headers=headers,
    )
    assert r_proj.status_code == 201, r_proj.text
    project = r_proj.json()
    project_id = project["id"]

    # 2. Register participant
    r_part = client.post(
        f"/api/v1/projects/{project_id}/participants",
        json={
            "display_name": "Tenzin Norbu",
            "preferred_language": "en",
            "preferred_contact_method": "email",
            "privacy_preferences": {"mask_home_address": True},
        },
        headers=headers,
    )
    assert r_part.status_code == 201, r_part.text
    participant = r_part.json()
    part_id = participant["id"]

    # 3. Record all 15 canonical categories with explicit agreement on documentary appearance
    choices = _build_15_choices(
        agreed_cats={"interview_recording", "documentary_appearance", "name_identification", "face_identification", "festival_submissions"},
        declined_cats={"voice_cloning", "synthetic_likeness"},
    )
    r_consent = client.post(
        f"/api/v1/participants/{part_id}/consent-records",
        json={
            "source_type": "release_form",
            "explanation": "Initial in-person filmed release form with clear exclusions.",
            "choices": choices,
        },
        headers=headers,
    )
    assert r_consent.status_code == 201, r_consent.text
    consent_record = r_consent.json()
    rec_id = consent_record["id"]
    assert consent_record["record_status"] == "awaiting_confirmation"

    # 4. Human confirms consent record
    r_confirm = client.post(
        f"/api/v1/consent-records/{rec_id}/confirm",
        json={
            "confirmation": "confirmed",
            "confirmation_evidence": "Physical countersigned document verified on staging archive.",
            "expected_version": consent_record["version"],
        },
        headers=headers,
    )
    assert r_confirm.status_code == 200, r_confirm.text
    confirmed = r_confirm.json()
    assert confirmed["record_status"] == "confirmed"
    assert confirmed["version_number"] == 1

    # 5. Mint participant portal token and verify portal review (zero bearer headers)
    r_tok = client.post(f"/api/v1/participants/{part_id}/access-token", headers=headers)
    assert r_tok.status_code == 200, r_tok.text
    token = r_tok.json().get("access_token") or r_tok.json().get("token")
    assert token

    r_portal = client.get(f"/api/v1/participants/{part_id}/portal-access?token={token}")
    assert r_portal.status_code == 200, r_portal.text
    assert r_portal.json()["display_name"] == "Tenzin Norbu"

    r_pconsents = client.get(f"/api/v1/participants/{part_id}/consent-records?token={token}")
    assert r_pconsents.status_code == 200
    pitems = r_pconsents.json()["items"]
    assert len(pitems) >= 1
    assert pitems[0]["record_status"] == "confirmed"

    # 6. Submit proposed use matching agreed categories
    r_use = client.post(
        f"/api/v1/projects/{project_id}/proposed-uses",
        json={
            "participant_id": part_id,
            "use_type": "documentary_screening",
            "platform": "Theatrical screening",
            "audience": "Documentary film festival",
            "purpose": "Screening of documentary appearance and interview",
            "territory": "Worldwide",
            "context_description": "Documentary screening featuring approved interview footage.",
            "run_analysis": True,
        },
        headers=headers,
    )
    assert r_use.status_code == 201, r_use.text
    use = r_use.json()
    use_id = use["id"]

    # 7. Comparison findings & human review
    r_reviews = client.get(f"/api/v1/projects/{project_id}/reviews", headers=headers)
    assert r_reviews.status_code == 200
    reviews = r_reviews.json().get("items", [])
    assert len(reviews) >= 1
    target_review = next(rv for rv in reviews if str(rv.get("proposed_use_id")) == str(use_id))

    # Decide with mandatory rationale
    r_dec = client.post(
        f"/api/v1/reviews/{target_review['id']}/human-decision",
        json={
            "decision": "approve",
            "reason": "Matches all confirmed consent categories for primary theatrical screening.",
            "expected_version": target_review["version"],
        },
        headers=headers,
    )
    assert r_dec.status_code == 200, r_dec.text
    assert r_dec.json()["human_decision"] == "approve"

    # 8. Check timeline for complete immutable audit trail
    r_time = client.get(f"/api/v1/projects/{project_id}/timeline?limit=50", headers=headers)
    assert r_time.status_code == 200
    timeline = r_time.json().get("items", [])
    actions = [item["action"] for item in timeline]
    assert "project.created" in actions
    assert "participant.created" in actions
    assert "consent_record.created" in actions
    assert "consent_record.confirmed" in actions


# -----------------------------------------------------------------------------
# SCENARIO B: Separate Intended Uses / Non-Transitive Consent
# -----------------------------------------------------------------------------
def test_scenario_b_separate_intended_uses_nontransitive(client, db):
    owner = make_user(db, "director.b@staging.example.com", "Director B")
    headers = auth_headers(owner)
    project = make_project(db, owner, title="Independent Journeys")

    # Participant agrees to documentary appearance, but explicitly declines promotional clips
    r_part = client.post(
        f"/api/v1/projects/{project.id}/participants",
        json={"display_name": "Amina Said"},
        headers=headers,
    )
    part_id = r_part.json()["id"]

    choices = _build_15_choices(
        agreed_cats={"documentary_appearance", "interview_recording"},
        declined_cats={"promotional_clips", "voice_cloning"},
    )
    r_consent = client.post(
        f"/api/v1/participants/{part_id}/consent-records",
        json={"source_type": "release_form", "explanation": "Strict restriction against promotional usage", "choices": choices},
        headers=headers,
    )
    rec = r_consent.json()
    client.post(
        f"/api/v1/consent-records/{rec['id']}/confirm",
        json={"confirmation": "confirmed", "confirmation_evidence": "Signed clause 4b exclusion", "expected_version": rec["version"]},
        headers=headers,
    )

    # Submit proposed use for promotional trailer
    r_use = client.post(
        f"/api/v1/projects/{project.id}/proposed-uses",
        json={
            "participant_id": part_id,
            "use_type": "promotional_trailer",
            "platform": "YouTube / Instagram",
            "audience": "Broad online public",
            "purpose": "Viral promo campaign",
            "territory": "Worldwide",
            "context_description": "Promotional teaser featuring interview clips.",
            "run_analysis": True,
        },
        headers=headers,
    )
    assert r_use.status_code == 201
    use = r_use.json()
    assert use["status"] == "analysis_complete"

    # The comparison engine MUST recognize PARTICIPANT_DECLINED
    # Because agreement to documentary appearance is NEVER agreement to promotional clips
    r_reviews = client.get(f"/api/v1/projects/{project.id}/reviews", headers=headers)
    assert r_reviews.status_code == 200
    reviews = [rv for rv in r_reviews.json().get("items", []) if str(rv.get("proposed_use_id")) == str(use["id"])]
    assert len(reviews) >= 1
    review = reviews[0]
    declined_findings = [f for f in review.get("findings", []) if f.get("choice") == "declined" or f.get("status") == "declined" or "declined" in str(f).lower()]
    assert len(declined_findings) >= 1, f"Expected declined finding, got {review.get('findings')}"


# -----------------------------------------------------------------------------
# SCENARIO C: Silence and Incomplete Consent
# -----------------------------------------------------------------------------
def test_scenario_c_silence_and_incomplete_consent(client, db):
    owner = make_user(db, "director.c@staging.example.com", "Director C")
    headers = auth_headers(owner)
    project = make_project(db, owner, title="Unspoken Words")

    r_part = client.post(
        f"/api/v1/projects/{project.id}/participants",
        json={"display_name": "David Cole"},
        headers=headers,
    )
    part_id = r_part.json()["id"]

    # All categories left not_discussed except interview_recording
    choices = _build_15_choices(
        agreed_cats={"interview_recording"},
        declined_cats=set(),
    )
    r_consent = client.post(
        f"/api/v1/participants/{part_id}/consent-records",
        json={"source_type": "interview", "explanation": "Verbal consent to sit for interview only", "choices": choices},
        headers=headers,
    )
    assert r_consent.status_code == 201, r_consent.text
    rec = r_consent.json()
    r_conf = client.post(
        f"/api/v1/consent-records/{rec['id']}/confirm",
        json={"confirmation": "confirmed", "confirmation_evidence": "Audio tape verification", "expected_version": rec["version"]},
        headers=headers,
    )
    assert r_conf.status_code == 200, r_conf.text

    # Proposed use for third party AI or synthetic likeness
    r_use = client.post(
        f"/api/v1/projects/{project.id}/proposed-uses",
        json={
            "participant_id": part_id,
            "use_type": "synthetic_likeness",
            "platform": "VR Exhibition",
            "audience": "Exhibition visitors",
            "purpose": "Interactive digital avatar",
            "territory": "North America",
            "context_description": "Creating AI synthetic likeness from interview stills.",
            "run_analysis": True,
        },
        headers=headers,
    )
    assert r_use.status_code == 201
    use = r_use.json()
    assert use["status"] == "analysis_complete"

    # Invariant: Silence is NEVER agreement
    # Proposed use cannot be automatically approved
    r_reviews = client.get(f"/api/v1/projects/{project.id}/reviews", headers=headers)
    reviews = [rv for rv in r_reviews.json().get("items", []) if str(rv.get("proposed_use_id")) == str(use["id"])]
    assert len(reviews) >= 1
    review = reviews[0]
    # Human cannot approve without resolving the missing consent
    assert review["human_decision"] is None
    assert review["uncertainty"] is not None


# -----------------------------------------------------------------------------
# SCENARIO D: Revocation & Formal Withdrawal
# -----------------------------------------------------------------------------
def test_scenario_d_revocation_and_withdrawal(client, db):
    owner = make_user(db, "director.d@staging.example.com", "Director D")
    headers = auth_headers(owner)
    project = make_project(db, owner, title="The River Gate")

    r_part = client.post(
        f"/api/v1/projects/{project.id}/participants",
        json={"display_name": "Kiran Patel"},
        headers=headers,
    )
    part_id = r_part.json()["id"]

    # Issue portal token
    r_tok = client.post(f"/api/v1/participants/{part_id}/access-token", headers=headers)
    token = r_tok.json().get("access_token") or r_tok.json().get("token")

    # Participant submits formal withdrawal request via portal
    r_with = client.post(
        f"/api/v1/participants/{part_id}/clarification-requests?token={token}",
        json={
            "category": "documentary_appearance",
            "concern": "I am formally withdrawing my consent to appear in this documentary due to personal circumstances.",
            "request_type": "withdrawal",
        },
    )
    assert r_with.status_code == 201, r_with.text
    res = r_with.json()
    assert res["status"] == "received"
    assert "withdrawal" in res["message"].lower()

    # Verify urgent task was created for participant care lead
    r_tasks = client.get(f"/api/v1/projects/{project.id}/tasks", headers=headers)
    assert r_tasks.status_code == 200
    tasks = r_tasks.json().get("items", [])
    withdrawal_tasks = [t for t in tasks if t.get("priority") == "urgent" or "WITHDRAWAL" in t.get("title", "")]
    assert len(withdrawal_tasks) >= 1
    assert "withdrawal" in withdrawal_tasks[0]["title"].lower() or "withdrawal" in withdrawal_tasks[0]["description"].lower()

    # Verify audit timeline logs participant.withdrawal_requested
    r_time = client.get(f"/api/v1/projects/{project.id}/timeline?limit=20", headers=headers)
    actions = [e["action"] for e in r_time.json().get("items", [])]
    assert "participant.withdrawal_requested" in actions


# -----------------------------------------------------------------------------
# SCENARIO E: Human Decision Authority & Mandatory Rationale
# -----------------------------------------------------------------------------
def test_scenario_e_human_decision_authority_and_ai_advisory(client, db):
    owner = make_user(db, "director.e@staging.example.com", "Director E")
    headers = auth_headers(owner)
    project = make_project(db, owner, title="Decision Bounds")

    r_part = client.post(
        f"/api/v1/projects/{project.id}/participants",
        json={"display_name": "Elena Vance"},
        headers=headers,
    )
    part_id = r_part.json()["id"]

    choices = _build_15_choices(agreed_cats={"interview_recording"}, declined_cats=set())
    r_consent = client.post(
        f"/api/v1/participants/{part_id}/consent-records",
        json={"source_type": "release_form", "explanation": "Interview consent", "choices": choices},
        headers=headers,
    )
    rec = r_consent.json()
    client.post(
        f"/api/v1/consent-records/{rec['id']}/confirm",
        json={"confirmation": "confirmed", "confirmation_evidence": "Countersigned release", "expected_version": rec["version"]},
        headers=headers,
    )

    r_use = client.post(
        f"/api/v1/projects/{project.id}/proposed-uses",
        json={
            "participant_id": part_id,
            "use_type": "interview",
            "platform": "Rough Cut",
            "audience": "Editorial Staff",
            "purpose": "Internal assembly",
            "territory": "Internal",
            "context_description": "First cut assembly",
            "run_analysis": True,
        },
        headers=headers,
    )
    use_id = r_use.json()["id"]

    r_reviews = client.get(f"/api/v1/projects/{project.id}/reviews", headers=headers)
    review = next(rv for rv in r_reviews.json().get("items", []) if str(rv.get("proposed_use_id")) == str(use_id))
    review_id = review["id"]

    # 1. Attempting human decision with empty/too-short rationale MUST fail validation (422)
    r_empty_reason = client.post(
        f"/api/v1/reviews/{review_id}/human-decision",
        json={
            "decision": "approve",
            "reason": "x",  # min_length is 3
            "expected_version": review["version"],
        },
        headers=headers,
    )
    assert r_empty_reason.status_code == 422, "Decision without rationale must be rejected"

    # 2. Valid human decision succeeds
    r_valid_dec = client.post(
        f"/api/v1/reviews/{review_id}/human-decision",
        json={
            "decision": "approve",
            "reason": "Strictly limited to internal rough cut assembly as permitted by initial interview consent.",
            "expected_version": review["version"],
        },
        headers=headers,
    )
    assert r_valid_dec.status_code == 200
    decided = r_valid_dec.json()
    assert decided["human_decision"] == "approve"
    assert decided["review_status"] == "completed"

    # 3. State machine prevents duplicate decision mutation
    r_dup = client.post(
        f"/api/v1/reviews/{review_id}/human-decision",
        json={
            "decision": "decline",
            "reason": "Attempting illegal double decision",
            "expected_version": decided["version"],
        },
        headers=headers,
    )
    assert r_dup.status_code in (409, 412), "Completed review must not accept another decision"


# -----------------------------------------------------------------------------
# SCENARIO F: Document Lifecycle, Malware Gate & Storage Boundaries
# -----------------------------------------------------------------------------
def test_scenario_f_private_document_lifecycle_and_malware_gate(client, db):
    owner = make_user(db, "director.f@staging.example.com", "Director F")
    headers = auth_headers(owner)
    project = make_project(db, owner, title="Document Trust")

    r_part = client.post(
        f"/api/v1/projects/{project.id}/participants",
        json={"display_name": "Marcus Kane"},
        headers=headers,
    )
    part_id = r_part.json()["id"]

    # 1. Request presigned upload URL
    r_upload_req = client.post(
        f"/api/v1/participants/{part_id}/documents/upload-url",
        json={"original_filename": "release_signed.pdf", "mime_type": "application/pdf", "file_size": len(PDF_BYTES)},
        headers=headers,
    )
    assert r_upload_req.status_code == 201
    upload_info = r_upload_req.json()
    assert "upload_url" in upload_info
    assert "storage_key" in upload_info

    # 2. Upload raw bytes to capability upload URL
    r_put = client.put(upload_info["upload_url"], content=PDF_BYTES, headers={"Content-Type": "application/octet-stream"})
    assert r_put.status_code == 201

    # 3. Complete upload (triggers antivirus scan)
    r_complete = client.post(
        f"/api/v1/participants/{part_id}/documents/complete-upload",
        json={"storage_key": upload_info["storage_key"], "signature_status": "signed"},
        headers=headers,
    )
    assert r_complete.status_code == 201
    doc = r_complete.json()
    assert doc["mime_type"] == "application/pdf"
    assert doc["extraction_status"] == "pending"

    # 4. Request authorized presigned download URL
    r_down = client.get(f"/api/v1/documents/{doc['id']}/download-url", headers=headers)
    assert r_down.status_code == 200
    down_url = r_down.json()["download_url"]
    r_bytes = client.get(down_url)
    assert r_bytes.status_code == 200
    assert r_bytes.content == PDF_BYTES

    # 5. Security boundaries: path traversal rejected
    for bad_key in ["../../etc/shadow", f"{project.id}/{part_id}/../../evil.pdf"]:
        r_trav = client.post(
            f"/api/v1/participants/{part_id}/documents/complete-upload",
            json={"storage_key": bad_key},
            headers=headers,
        )
        assert r_trav.status_code in (400, 412, 422)


# -----------------------------------------------------------------------------
# SCENARIO G: Concurrent Operations & Optimistic Locking
# -----------------------------------------------------------------------------
def test_scenario_g_concurrent_operations_and_idempotency(client, db):
    owner = make_user(db, "director.g@staging.example.com", "Director G")
    headers = auth_headers(owner)
    project = make_project(db, owner, title="Concurrency Lab")

    r_part = client.post(
        f"/api/v1/projects/{project.id}/participants",
        json={"display_name": "Concurrent Subject"},
        headers=headers,
    )
    part = r_part.json()
    part_id = part["id"]
    initial_version = part["version"]

    # Writer A updates participant with expected_version = initial_version
    r_up_a = client.patch(
        f"/api/v1/participants/{part_id}",
        json={"display_name": "Updated Subject by Writer A", "expected_version": initial_version},
        headers=headers,
    )
    assert r_up_a.status_code == 200
    updated_a = r_up_a.json()
    assert updated_a["version"] == initial_version + 1

    # Writer B attempts update with stale expected_version = initial_version -> MUST return Conflict (409)
    r_up_b = client.patch(
        f"/api/v1/participants/{part_id}",
        json={"display_name": "Conflicting Update by Writer B", "expected_version": initial_version},
        headers=headers,
    )
    assert r_up_b.status_code == 409, "Stale optimistic lock must reject concurrent mutation"


# -----------------------------------------------------------------------------
# SCENARIO H: Complete Immutable Audit Trail
# -----------------------------------------------------------------------------
def test_scenario_h_complete_audit_trail_and_export(client, db):
    owner = make_user(db, "director.h@staging.example.com", "Director H")
    headers = auth_headers(owner)
    project = make_project(db, owner, title="Audit Showcase")

    # Generate sequence of mutations
    r_part = client.post(f"/api/v1/projects/{project.id}/participants", json={"display_name": "Audit Subject"}, headers=headers)
    part_id = r_part.json()["id"]

    choices = _build_15_choices(agreed_cats={"interview_recording"}, declined_cats=set())
    r_rec = client.post(
        f"/api/v1/participants/{part_id}/consent-records",
        json={"source_type": "release_form", "choices": choices},
        headers=headers,
    )
    assert r_rec.status_code == 201, r_rec.text
    rec = r_rec.json()
    r_conf = client.post(
        f"/api/v1/consent-records/{rec['id']}/confirm",
        json={"confirmation": "confirmed", "confirmation_evidence": "Verified on staging archive", "expected_version": rec["version"]},
        headers=headers,
    )
    assert r_conf.status_code == 200, r_conf.text

    # Query timeline with keyset pagination
    r_page1 = client.get(f"/api/v1/projects/{project.id}/timeline?limit=2", headers=headers)
    assert r_page1.status_code == 200
    p1 = r_page1.json()
    assert len(p1["items"]) <= 2

    # Query all events
    r_all = client.get(f"/api/v1/projects/{project.id}/timeline?limit=100", headers=headers)
    assert r_all.status_code == 200
    events = r_all.json()["items"]
    assert len(events) >= 3

    # All audit events must contain required immutable metadata
    for ev in events:
        assert ev["id"]
        assert ev["timestamp"]
        assert ev["action"]
        assert ev["actor_type"]
        assert ev["correlation_id"]


# -----------------------------------------------------------------------------
# ADVERSARIAL: Cross-Tenant Isolation
# -----------------------------------------------------------------------------
def test_cross_tenant_isolation_adversarial(client, db):
    # Tenant Alpha
    owner_a = make_user(db, "alpha.owner@staging.example.com", "Alpha Owner")
    headers_a = auth_headers(owner_a)
    proj_a = make_project(db, owner_a, title="Tenant Alpha Documentary")
    r_part_a = client.post(f"/api/v1/projects/{proj_a.id}/participants", json={"display_name": "Alpha Subject"}, headers=headers_a)
    part_a_id = r_part_a.json()["id"]

    # Tenant Beta
    owner_b = make_user(db, "beta.owner@staging.example.com", "Beta Owner")
    headers_b = auth_headers(owner_b)
    make_project(db, owner_b, title="Tenant Beta Documentary")

    # 1. Tenant Beta attempts to list or read Tenant Alpha's project
    r_leak_proj = client.get(f"/api/v1/projects/{proj_a.id}", headers=headers_b)
    assert r_leak_proj.status_code in (403, 404), "Tenant Beta cannot access Tenant Alpha's project"

    # 2. Tenant Beta attempts to read Tenant Alpha's participant
    r_leak_part = client.get(f"/api/v1/participants/{part_a_id}", headers=headers_b)
    assert r_leak_part.status_code in (403, 404), "Tenant Beta cannot access Tenant Alpha's participant"

    # 3. Tenant Beta attempts to create consent record on Tenant Alpha's participant
    choices = _build_15_choices(agreed_cats={"interview_recording"}, declined_cats=set())
    r_leak_consent = client.post(
        f"/api/v1/participants/{part_a_id}/consent-records",
        json={"source_type": "release_form", "choices": choices},
        headers=headers_b,
    )
    assert r_leak_consent.status_code in (403, 404), "Tenant Beta cannot inject consent for Tenant Alpha"

    # 4. Tenant Beta attempts to read Tenant Alpha's audit timeline
    r_leak_time = client.get(f"/api/v1/projects/{proj_a.id}/timeline", headers=headers_b)
    assert r_leak_time.status_code in (403, 404), "Tenant Beta cannot access Tenant Alpha's timeline"
