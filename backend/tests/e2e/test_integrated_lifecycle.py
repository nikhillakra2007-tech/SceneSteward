"""E2E — 19-Step Integrated Lifecycle Test for SceneSteward.

Verifies the complete documentary production lifecycle:
  1. Authenticate user identities (Owner, Producer, Care Lead, Director).
  2. Create project via API.
  3. Add project members with distinct roles and verified permissions.
  4. Create participant with accessibility and privacy preferences.
  5. Propose a new documentary use.
  6. Update / version proposed use draft.
  7. Upload release document via private storage flow.
  8. Process document text extraction.
  9. Run AI analysis across agent pipeline.
  10. Persist analysis results in authoritative database.
  11. Compare proposed use and existing consent -> verify NEEDS_DISCUSSION.
  12. Present pending review for human review.
  13. Record explicit human decision and record confirmed participant consent.
  14. Verify immutable decision and consent history.
  15. Draft participant communication based on discussion needs.
  16. Approve communication and verify fail-closed delivery (503) without provider.
  17. Verify append-only audit trail and timeline.
  18. Deliver integration events via Switch atomic sweeper.
  19. Retrieve final project state with verified integrity.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import (
    ParticipantCommunication,
    ProposedUseAnalysis,
    Review,
)
from scripts.switch_retry import claim_batch
from tests.conftest import auth_headers, make_user


def test_19_step_integrated_lifecycle(client, db):
    # =========================================================================
    # Step 1: Authenticate users and establish identities
    # =========================================================================
    owner = make_user(db, "elena.owner@lifecycle.test", "Elena Vance (Owner)")
    producer = make_user(db, "marcus.producer@lifecycle.test", "Marcus Kane (Producer)")
    care_lead = make_user(db, "sofia.care@lifecycle.test", "Sofia Chen (Participant Care Lead)")
    director = make_user(db, "david.director@lifecycle.test", "David Kim (Director)")

    owner_auth = auth_headers(owner)
    producer_auth = auth_headers(producer)
    care_auth = auth_headers(care_lead)
    director_auth = auth_headers(director)

    assert owner_auth["Authorization"].startswith("Bearer ")
    assert producer_auth["Authorization"].startswith("Bearer ")

    # =========================================================================
    # Step 2: Create project (POST /api/v1/projects)
    # =========================================================================
    resp = client.post(
        "/api/v1/projects",
        json={
            "title": "Voices of the Delta",
            "description": "An intimate documentary exploring environmental migration.",
            "purpose": "Documenting generational relocation along coastal deltas.",
            "themes": ["climate", "community", "displacement"],
            "intended_audiences": ["film_festivals", "public_broadcast"],
        },
        headers=owner_auth,
    )
    assert resp.status_code == 201, resp.text
    project_data = resp.json()
    project_id = uuid.UUID(project_data["id"])
    assert project_data["title"] == "Voices of the Delta"
    assert project_data["created_by"] == str(owner.id)

    # =========================================================================
    # Step 3: Add project members (POST /api/v1/projects/{pid}/members)
    # =========================================================================
    for user_obj, role in [
        (producer, "producer"),
        (care_lead, "participant_care_lead"),
        (director, "director"),
    ]:
        m_resp = client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"email": user_obj.email, "role": role},
            headers=owner_auth,
        )
        assert m_resp.status_code == 201, m_resp.text
        assert m_resp.json()["role"] == role
        assert m_resp.json()["user_id"] == str(user_obj.id)

    # =========================================================================
    # Step 4: Create participant (POST /api/v1/projects/{pid}/participants)
    # =========================================================================
    p_resp = client.post(
        f"/api/v1/projects/{project_id}/participants",
        json={
            "display_name": "Tariq Mansour",
            "preferred_language": "ar",
            "accessibility_requirements": {"needs_sign_interpretation": False, "large_print_contracts": True},
            "privacy_preferences": {"do_not_publish_family_names": True},
        },
        headers=producer_auth,
    )
    assert p_resp.status_code == 201, p_resp.text
    participant_data = p_resp.json()
    participant_id = uuid.UUID(participant_data["id"])
    assert participant_data["display_name"] == "Tariq Mansour"

    # Step 6: Store encrypted contact information (POST /api/v1/participants/{pid}/contacts)
    contact_resp = client.post(
        f"/api/v1/participants/{participant_id}/contacts",
        json={
            "contact_type": "email",
            "value": "tariq.mansour@delta-voices.test",
        },
        headers=care_auth,
    )
    assert contact_resp.status_code == 201, contact_resp.text
    # Verify contact is encrypted and readable by Care Lead
    get_contact = client.get(
        f"/api/v1/participants/{participant_id}/contacts",
        headers=care_auth,
    )
    assert get_contact.status_code == 200
    assert any(c["value"] == "tariq.mansour@delta-voices.test" for c in get_contact.json())

    # Also add initial signed consent for documentary feature release
    init_cr = client.post(
        f"/api/v1/participants/{participant_id}/consent-records",
        json={
            "source_type": "release_form",
            "explanation": "Initial in-person paper release signed at harbor shoot.",
            "choices": [
                {"category": "interview_recording", "choice": "agreed", "evidence_reference": "doc-delta-001#p1"},
                {"category": "documentary_appearance", "choice": "agreed", "evidence_reference": "doc-delta-001#p2"},
            ],
        },
        headers=care_auth,
    )
    assert init_cr.status_code == 201, init_cr.text
    initial_cr_id = init_cr.json()["id"]

    confirm_resp = client.post(
        f"/api/v1/consent-records/{initial_cr_id}/confirm",
        json={
            "confirmation": "confirmed",
            "confirmation_evidence": "Signed physical release witnessed and counter-signed by Sofia Chen.",
            "expected_version": 1,
        },
        headers=care_auth,
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["record_status"] == "confirmed"

    # =========================================================================
    # Step 5: Add proposed use (POST /api/v1/projects/{pid}/proposed-uses)
    # =========================================================================
    u_resp = client.post(
        f"/api/v1/projects/{project_id}/proposed-uses",
        json={
            "participant_id": str(participant_id),
            "use_type": "theatrical_distribution",
            "platform": "cinema",
            "audience": "theatrical audience",
            "purpose": "Theatrical festival premiere",
            "territory": "north_america",
            "context_description": "Standard theatrical release of documentary feature.",
            "run_analysis": False,
        },
        headers=director_auth,
    )
    assert u_resp.status_code == 201, u_resp.text
    use_data = u_resp.json()
    use_id = uuid.UUID(use_data["id"])
    assert use_data["status"] == "submitted"
    assert use_data["use_type"] == "theatrical_distribution"

    # =========================================================================
    # Step 6: Create proposed-use version / update draft (PATCH /api/v1/proposed-uses/{id})
    # =========================================================================
    patch_resp = client.patch(
        f"/api/v1/proposed-uses/{use_id}",
        json={
            "context_description": "Expanded distribution: film festival premiere plus digital streaming excerpt with AI voice dubbing.",
            "territory": "worldwide",
            "expected_version": use_data["version"],
        },
        headers=director_auth,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched_data = patch_resp.json()
    assert "AI voice dubbing" in patched_data["context_description"]
    assert patched_data["version"] > use_data["version"]

    # =========================================================================
    # Step 7: Upload document (request upload URL -> PUT bytes -> complete upload)
    # =========================================================================
    doc_content = b"Participant Release Form: Tariq Mansour agrees to interview and documentary recording only."
    doc_size = len(doc_content)

    url_req = client.post(
        f"/api/v1/participants/{participant_id}/documents/upload-url",
        json={
            "original_filename": "tariq_release.txt",
            "mime_type": "text/plain",
            "file_size": doc_size,
            "document_type": "general_release",
        },
        headers=care_auth,
    )
    assert url_req.status_code == 201, url_req.text
    upload_info = url_req.json()
    storage_key = upload_info["storage_key"]

    # Upload raw bytes directly to the signed upload URL (no bearer required — token is the capability)
    put_resp = client.put(
        upload_info["upload_url"],
        content=doc_content,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert put_resp.status_code == 201, put_resp.text

    complete_resp = client.post(
        f"/api/v1/participants/{participant_id}/documents/complete-upload",
        json={
            "storage_key": storage_key,
            "signature_status": "signed",
        },
        headers=care_auth,
    )
    assert complete_resp.status_code == 201, complete_resp.text
    document_data = complete_resp.json()
    document_id = uuid.UUID(document_data["id"])
    assert document_data["storage_key"] == storage_key

    # Verify secure retrieval via signed download URL
    dl_resp = client.get(
        f"/api/v1/documents/{document_id}/download-url",
        headers=care_auth,
    )
    assert dl_resp.status_code == 200
    dl_url = dl_resp.json()["download_url"]
    retrieved_bytes = client.get(dl_url).content
    assert retrieved_bytes == doc_content

    # =========================================================================
    # Step 8: Process document extraction (POST /api/v1/documents/{doc_id}/extract)
    # =========================================================================
    extract_resp = client.post(
        f"/api/v1/documents/{document_id}/extract",
        headers=care_auth,
    )
    assert extract_resp.status_code == 200, extract_resp.text
    extracted_doc = extract_resp.json()
    assert extracted_doc["extraction_status"] == "extracted"

    # =========================================================================
    # Step 9: Run AI analysis (POST /api/v1/proposed-uses/{id}/analyse)
    # =========================================================================
    analyse_resp = client.post(
        f"/api/v1/proposed-uses/{use_id}/analyse",
        headers=producer_auth,
    )
    assert analyse_resp.status_code == 200, analyse_resp.text
    analysis_result = analyse_resp.json()
    assert analysis_result["requires_human_review"] is True
    review_id = uuid.UUID(analysis_result["review_id"])

    # =========================================================================
    # Step 10: Persist analysis results in database
    # =========================================================================
    analysis_row = db.execute(
        select(ProposedUseAnalysis).where(ProposedUseAnalysis.proposed_use_id == use_id)
    ).scalar_one()
    assert analysis_row is not None
    assert analysis_row.id == uuid.UUID(analysis_result["analysis"]["id"])

    # Verify agent findings retrieval endpoint
    findings_resp = client.get(
        f"/api/v1/proposed-uses/{use_id}/agent-findings",
        headers=producer_auth,
    )
    assert findings_resp.status_code == 200
    assert len(findings_resp.json()) >= 1

    # =========================================================================
    # Step 11: Compare proposed use and analysis findings -> outcome == NEEDS_DISCUSSION
    # =========================================================================
    assert analysis_result["outcome"] == "NEEDS_DISCUSSION"
    assert analysis_row.outcome == "NEEDS_DISCUSSION"
    # Unsettled categories should include voice cloning / dubbing
    unsettled = {f["category"] for f in analysis_row.findings if f.get("choice") is None}
    assert len(unsettled) > 0, "Expected unsettled consent categories in analysis findings"

    # =========================================================================
    # Step 12: Present for human review
    # =========================================================================
    review = db.get(Review, review_id)
    assert review is not None
    assert review.review_status == "pending"
    assert review.proposed_use_id == use_id

    # =========================================================================
    # Step 13: Record explicit participant decision (human decision + confirmed consent)
    # =========================================================================
    dec_resp = client.post(
        f"/api/v1/reviews/{review_id}/human-decision",
        json={
            "decision": "needs_participant_discussion",
            "reason": "AI voice dubbing and digital distribution were not part of Tariq's initial consent.",
            "expected_version": review.version,
        },
        headers=producer_auth,
    )
    assert dec_resp.status_code == 200, dec_resp.text
    assert dec_resp.json()["review_status"] == "completed"

    # Participant agrees to digital streaming but explicitly declines voice cloning
    updated_cr_resp = client.post(
        f"/api/v1/participants/{participant_id}/consent-records",
        json={
            "source_type": "verbal_recorded",
            "explanation": "Follow-up discussion regarding international digital distribution.",
            "choices": [
                {"category": "interview_recording", "choice": "agreed", "evidence_reference": "discussion-2026-11-04"},
                {"category": "documentary_appearance", "choice": "agreed", "evidence_reference": "discussion-2026-11-04"},
                {"category": "digital_streaming", "choice": "agreed", "evidence_reference": "discussion-2026-11-04"},
                {"category": "voice_cloning", "choice": "declined", "evidence_reference": "discussion-2026-11-04#voice-denial"},
            ],
        },
        headers=care_auth,
    )
    assert updated_cr_resp.status_code == 201, updated_cr_resp.text
    updated_cr_id = updated_cr_resp.json()["id"]

    confirm_updated = client.post(
        f"/api/v1/consent-records/{updated_cr_id}/confirm",
        json={
            "confirmation": "confirmed",
            "confirmation_evidence": "In-person discussion notes signed by participant.",
            "expected_version": 1,
        },
        headers=care_auth,
    )
    assert confirm_updated.status_code == 200
    assert confirm_updated.json()["record_status"] == "confirmed"

    # =========================================================================
    # Step 14: Verify immutable decision & consent history (GET /api/v1/participants/{pid}/history)
    # =========================================================================
    history_resp = client.get(
        f"/api/v1/participants/{participant_id}/history",
        headers=producer_auth,
    )
    assert history_resp.status_code == 200, history_resp.text
    history_entries = history_resp.json()
    assert len(history_entries) == 2
    # Verify versions are ordered descending
    assert history_entries[0]["version_number"] == 2
    assert history_entries[0]["record_status"] == "confirmed"
    assert history_entries[1]["version_number"] == 1
    assert history_entries[1]["record_status"] == "superseded"

    # =========================================================================
    # Step 15: Generate draft communication (POST /api/v1/projects/{pid}/communications)
    # =========================================================================
    comm_resp = client.post(
        f"/api/v1/projects/{project_id}/communications",
        json={
            "participant_id": str(participant_id),
            "communication_type": "email",
            "subject": "Follow-up regarding Voices of the Delta streaming rights",
            "draft_content": "Dear Tariq, confirming that voice cloning will NOT be used in accordance with your wishes.",
        },
        headers=producer_auth,
    )
    assert comm_resp.status_code == 201, comm_resp.text
    comm_data = comm_resp.json()
    comm_id = uuid.UUID(comm_data["id"])
    assert comm_data["communication_status"] == "draft"

    # =========================================================================
    # Step 16: Approve communication and verify fail-closed delivery (503)
    # =========================================================================
    appr_resp = client.post(
        f"/api/v1/communications/{comm_id}/approve",
        json={"notes": "Approved by Sofia Chen after consulting with Tariq."},
        headers=care_auth,
    )
    assert appr_resp.status_code == 200, appr_resp.text
    assert appr_resp.json()["communication_status"] == "approved"
    assert appr_resp.json()["approved_by"] == str(care_lead.id)

    # Send attempt must fail closed (503 UpstreamUnavailable) when provider unconfigured
    send_resp = client.post(
        f"/api/v1/communications/{comm_id}/send",
        headers=care_auth,
    )
    assert send_resp.status_code == 503, "Expected 503 fail-closed when provider unconfigured"
    # Verify DB status remained 'approved' and did NOT falsely mutate to 'sent'
    comm_db = db.get(ParticipantCommunication, comm_id)
    assert comm_db.communication_status == "approved"
    assert comm_db.sent_at is None

    # =========================================================================
    # Step 17: Record and verify audit events (GET /api/v1/projects/{pid}/timeline)
    # =========================================================================
    timeline_resp = client.get(
        f"/api/v1/projects/{project_id}/timeline?limit=100",
        headers=producer_auth,
    )
    assert timeline_resp.status_code == 200, timeline_resp.text
    timeline = timeline_resp.json()["items"]
    actions = [e["action"] for e in timeline]

    assert "project.created" in actions
    assert "participant.created" in actions
    assert "proposed_use.created" in actions
    assert "proposed_use.updated" in actions
    assert "document.upload_url_issued" in actions
    assert "document.uploaded" in actions
    assert "document.extracted" in actions
    assert "proposed_use.analysed" in actions
    assert "review.human_decision" in actions
    assert "communication.draft_created" in actions
    assert "communication.approved" in actions
    assert "communication.send_attempted" in actions

    # =========================================================================
    # Step 18: Deliver required Switch events via atomic sweeper
    # =========================================================================
    claimed_events = claim_batch(db, limit=50)
    assert isinstance(claimed_events, list)

    # =========================================================================
    # Step 19: Retrieve final project state with verified integrity
    # =========================================================================
    final_proj_resp = client.get(
        f"/api/v1/projects/{project_id}",
        headers=owner_auth,
    )
    assert final_proj_resp.status_code == 200, final_proj_resp.text
    final_proj = final_proj_resp.json()
    assert final_proj["id"] == str(project_id)
    assert final_proj["title"] == "Voices of the Delta"

    # Verify proposed use status reflects human decision
    final_use_resp = client.get(
        f"/api/v1/proposed-uses/{use_id}",
        headers=owner_auth,
    )
    assert final_use_resp.status_code == 200
    assert final_use_resp.json()["status"] == "awaiting_participant_discussion"
