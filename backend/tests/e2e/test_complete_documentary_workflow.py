"""Complete End-to-End Documentary Lifecycle Integration Test.

Verifies the 8-step core lifecycle of SceneSteward:
1. Production staff authentication and project workspace initialization.
2. Participant registration in PostgreSQL with language and accessibility preferences.
3. Recording and confirming 15 canonical categories of consent (mix of agreed, declined, not_discussed).
4. Proposing a new footage/likeness use (e.g. promotional clip with AI voice cloning).
5. SceneSteward comparison engine analysis verifying invariant:
   "A participant's agreement to one use must never automatically become agreement to another.
    Silence is never agreement."
   Flags PARTICIPANT_DECLINED and NEEDS_DISCUSSION findings.
6. Human review decision state machine with mandatory rationale (AI never auto-approves).
7. Participant care communication drafting, mandatory human approval, and fail-closed send behavior.
8. Cryptographic participant transparency portal access, token authentication, clarification submission,
   and immutable audit timeline verification.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.choices import CONSENT_CATEGORIES
from app.models import (
    AuditEvent,
    Participant,
    ParticipantCommunication,
    ProposedUseAnalysis,
    Review,
    Task,
)
from tests.conftest import auth_headers, make_user


@pytest.fixture()
def setup_documentary_workspace(client, db):
    owner = make_user(db, "director.elena@scenesteward.com", "Elena Director")
    producer = make_user(db, "producer.marcus@scenesteward.com", "Marcus Producer")
    care_lead = make_user(db, "care.sarah@scenesteward.com", "Sarah Care Lead")

    # Step 1: Create project workspace
    res = client.post(
        "/api/v1/projects",
        json={
            "title": "Voices of the Watershed",
            "description": "An investigative documentary on community resilience and river ecology.",
            "purpose": "Documentary feature film and educational outreach",
            "themes": ["ecology", "indigenous knowledge", "water rights"],
            "intended_audiences": ["theatrical", "film festivals", "educational broadcast"],
            "distribution_plan": "North American festival premiere followed by public broadcast.",
        },
        headers=auth_headers(owner),
    )
    assert res.status_code == 201, res.text
    project = res.json()
    project_id = uuid.UUID(project["id"])

    # Add members
    from app.models import ProjectMembership
    db.add(ProjectMembership(project_id=project_id, user_id=producer.id, role="producer",
                             membership_status="active", invited_by=owner.id))
    db.add(ProjectMembership(project_id=project_id, user_id=care_lead.id, role="participant_care_lead",
                             membership_status="active", invited_by=owner.id))
    db.commit()

    return {
        "owner": owner,
        "producer": producer,
        "care_lead": care_lead,
        "project": project,
        "project_id": project_id,
    }


def test_complete_8_step_documentary_workflow(client, db, setup_documentary_workspace):
    ctx = setup_documentary_workspace
    owner = ctx["owner"]
    producer = ctx["producer"]
    care_lead = ctx["care_lead"]
    pid_str = ctx["project"]["id"]
    pid = ctx["project_id"]

    # =========================================================================
    # STEP 1: Authentication & Workspace Governance
    # =========================================================================
    res_me = client.get("/api/v1/auth/me", headers=auth_headers(owner))
    assert res_me.status_code == 200
    assert res_me.json()["email"] == owner.email

    res_proj = client.get(f"/api/v1/projects/{pid_str}", headers=auth_headers(producer))
    assert res_proj.status_code == 200
    assert res_proj.json()["title"] == "Voices of the Watershed"

    # =========================================================================
    # STEP 2: Participant Registration in PostgreSQL
    # =========================================================================
    res_part = client.post(
        f"/api/v1/projects/{pid_str}/participants",
        json={
            "display_name": "Dr. Miriam Kalu (fictional)",
            "preferred_language": "en",
            "preferred_contact_method": "email",
            "accessibility_requirements": {"subtitles_required": True},
            "privacy_preferences": {"mask_home_address": True, "no_family_filming": True},
        },
        headers=auth_headers(owner),
    )
    assert res_part.status_code == 201, res_part.text
    part_data = res_part.json()
    participant_id = uuid.UUID(part_data["id"])
    assert part_data["participant_status"] == "active"
    assert part_data["display_name"] == "Dr. Miriam Kalu (fictional)"

    # Verify database persistence
    part_db = db.get(Participant, participant_id)
    assert part_db is not None
    assert part_db.project_id == pid

    # =========================================================================
    # STEP 3: Record and Confirm 15 Canonical Consent Categories
    # =========================================================================
    # Categorization breakdown:
    # AGREED: interview_recording, documentary_appearance, name_identification, face_identification, festival_submissions
    # DECLINED: voice_cloning, synthetic_likeness, third_party_ai_processing
    # NOT_DISCUSSED / UNRESOLVED: promotional_clips, new_audience, new_territory, new_platform, new_story_context, sensitive_personal_details, ai_transcription
    consent_choices = [
        {"category": "interview_recording", "choice": "agreed", "explanation": "Agreed to in-depth sit-down interview."},
        {"category": "documentary_appearance", "choice": "agreed", "explanation": "Agreed to feature in primary documentary."},
        {"category": "name_identification", "choice": "agreed", "explanation": "Full professional title and name attribution permitted."},
        {"category": "face_identification", "choice": "agreed", "explanation": "Unmasked on-camera appearance permitted."},
        {"category": "festival_submissions", "choice": "agreed", "explanation": "Festival screenings approved."},
        {"category": "voice_cloning", "choice": "declined", "explanation": "Explicitly refused any AI synthetic voice recreation."},
        {"category": "synthetic_likeness", "choice": "declined", "explanation": "No deepfake or avatar recreation."},
        {"category": "third_party_ai_processing", "choice": "declined", "explanation": "Footage must not be fed into external generative models."},
        {"category": "promotional_clips", "choice": "not_discussed"},
        {"category": "sensitive_personal_details", "choice": "not_discussed"},
        {"category": "ai_transcription", "choice": "not_discussed"},
        {"category": "new_audience", "choice": "not_discussed"},
        {"category": "new_territory", "choice": "not_discussed"},
        {"category": "new_platform", "choice": "not_discussed"},
        {"category": "new_story_context", "choice": "not_discussed"},
    ]
    assert len(consent_choices) == 15
    assert {c["category"] for c in consent_choices} == set(CONSENT_CATEGORIES)

    res_consent = client.post(
        f"/api/v1/participants/{participant_id}/consent-records",
        json={
            "source_type": "release_form",
            "explanation": "Standard production participant release signed with explicit exclusions.",
            "choices": consent_choices,
        },
        headers=auth_headers(care_lead),
    )
    assert res_consent.status_code == 201, res_consent.text
    consent_data = res_consent.json()
    consent_id = uuid.UUID(consent_data["id"])
    assert consent_data["record_status"] == "awaiting_confirmation"

    # Care lead confirms consent record
    res_confirm = client.post(
        f"/api/v1/consent-records/{consent_id}/confirm",
        json={
            "confirmation": "confirmed",
            "confirmation_evidence": "Signed physical release on file; witnessed by Care Lead.",
            "expected_version": consent_data["version"],
        },
        headers=auth_headers(care_lead),
    )
    assert res_confirm.status_code == 200, res_confirm.text
    assert res_confirm.json()["record_status"] == "confirmed"

    # =========================================================================
    # STEP 4: Propose New Footage / Likeness Use
    # =========================================================================
    # Production seeks to use Dr. Miriam Kalu's interview in a social promotional clip with synthetic voice augmentation
    res_use = client.post(
        f"/api/v1/projects/{pid_str}/proposed-uses",
        json={
            "participant_id": str(participant_id),
            "use_type": "promotional_clips",
            "platform": "TikTok & Instagram Reels",
            "audience": "Global youth and social media audience",
            "purpose": "Viral teaser promotional marketing campaign",
            "territory": "Worldwide",
            "context_description": "Promotional short video snippet paired with AI voice cloning to deliver dramatized hook.",
            "run_analysis": True,
        },
        headers=auth_headers(producer),
    )
    assert res_use.status_code == 201, res_use.text
    use_data = res_use.json()
    use_id = uuid.UUID(use_data["id"])
    assert use_data["status"] == "analysis_complete"

    # =========================================================================
    # STEP 5: Verification of SceneSteward Invariant & Automated Comparison Engine
    # =========================================================================
    analysis = db.execute(
        select(ProposedUseAnalysis)
        .where(ProposedUseAnalysis.proposed_use_id == use_id)
        .order_by(ProposedUseAnalysis.created_at.desc())
        .limit(1)
    ).scalar_one()

    # Invariant: Agreement to documentary appearance is NEVER agreement to promotional clips or voice cloning
    assert analysis.outcome in ("NEEDS_DISCUSSION", "PARTICIPANT_DECLINED")

    # Check findings details
    findings = analysis.findings
    assert isinstance(findings, list) and len(findings) > 0

    # Invariant: Silence is never agreement.
    # Unanswered/unsettled categories must default to UNRESOLVED or NEEDS_DISCUSSION
    unsettled_findings = [f for f in findings if f.get("choice") in (None, "not_discussed")]
    assert len(unsettled_findings) >= 1

    # =========================================================================
    # STEP 6: Advisory Agents & Binding Human Review Gate
    # =========================================================================
    # Verify advisory agent findings are recorded
    res_findings = client.get(
        f"/api/v1/proposed-uses/{use_id}/agent-findings",
        headers=auth_headers(producer),
    )
    assert res_findings.status_code == 200
    agent_findings = res_findings.json()
    assert len(agent_findings) >= 1

    # Verify a Human Review was queued
    review = db.execute(
        select(Review).where(Review.proposed_use_id == use_id)
    ).scalar_one()
    assert review.review_status == "pending"
    assert review.human_decision is None

    # Automated agents can NEVER make binding approval/decline decisions
    # Staff MUST submit a binding human decision with mandatory written rationale
    mandatory_rationale = (
        "Declined AI voice cloning as Dr. Miriam Kalu explicitly refused synthetic recreation in release form. "
        "Promotional clip usage requires separate direct consultation with participant before edit lock."
    )
    res_decision = client.post(
        f"/api/v1/reviews/{review.id}/human-decision",
        json={
            "decision": "needs_participant_discussion",
            "reason": mandatory_rationale,
            "expected_version": review.version,
        },
        headers=auth_headers(owner),
    )
    assert res_decision.status_code == 200, res_decision.text
    decided_review = res_decision.json()
    assert decided_review["review_status"] == "completed"
    assert decided_review["human_decision"] == "needs_participant_discussion"
    assert decided_review["decision_reason"] == mandatory_rationale

    # Invariant: Terminal review state machine - a decided review cannot be overwritten
    res_duplicate_decision = client.post(
        f"/api/v1/reviews/{review.id}/human-decision",
        json={
            "decision": "approve",
            "reason": "Attempting to reverse human decision without re-opening review",
            "expected_version": decided_review["version"],
        },
        headers=auth_headers(owner),
    )
    assert res_duplicate_decision.status_code in (409, 412)

    # =========================================================================
    # STEP 7: Participant Care Communication & Outbound Fail-Closed Delivery
    # =========================================================================
    # Care lead drafts message to participant
    res_comm = client.post(
        f"/api/v1/projects/{pid_str}/communications",
        json={
            "participant_id": str(participant_id),
            "communication_type": "email",
            "subject": "Follow-up regarding promotional clip proposal",
            "draft_content": (
                "Dear Dr. Miriam Kalu,\n\nOur production team is preparing short social clips. "
                "Because your agreement did not cover promotional excerpts and strictly excluded synthetic voice tools, "
                "we will not use any AI tools and would like to invite your feedback on a preliminary edit.\n\n"
                "Warm regards,\nSarah (Participant Care Lead)"
            ),
        },
        headers=auth_headers(care_lead),
    )
    assert res_comm.status_code == 201, res_comm.text
    comm_data = res_comm.json()
    comm_id = uuid.UUID(comm_data["id"])
    assert comm_data["communication_status"] == "draft"
    assert comm_data["approved_by"] is None

    # Step 7b: Invariant - Unapproved communication can NEVER be sent
    res_unapproved_send = client.post(
        f"/api/v1/communications/{comm_id}/send",
        headers=auth_headers(care_lead),
    )
    assert res_unapproved_send.status_code in (412, 400)

    # Step 7c: Human explicitly approves the communication
    res_approve_comm = client.post(
        f"/api/v1/communications/{comm_id}/approve",
        json={"notes": "Authorized by Participant Care Lead"},
        headers=auth_headers(care_lead),
    )
    assert res_approve_comm.status_code == 200, res_approve_comm.text
    approved_comm = res_approve_comm.json()
    assert approved_comm["communication_status"] == "approved"
    assert approved_comm["approved_by"] is not None

    # Step 7d: Invariant - Sending without configured provider fails closed (503) without mutating status to sent
    res_send_attempt = client.post(
        f"/api/v1/communications/{comm_id}/send",
        headers=auth_headers(care_lead),
    )
    assert res_send_attempt.status_code == 503

    # Verify DB status remained 'approved' (fail-closed, never falsely claim sent)
    comm_db = db.get(ParticipantCommunication, comm_id)
    assert comm_db.communication_status == "approved"
    assert comm_db.sent_at is None

    # =========================================================================
    # STEP 8: Participant Transparency Portal & Immutable Keyset Audit Trail
    # =========================================================================
    # Step 8a: Mint signed participant access token
    res_token = client.post(
        f"/api/v1/participants/{participant_id}/access-token",
        headers=auth_headers(care_lead),
    )
    assert res_token.status_code == 200, res_token.text
    token_data = res_token.json()
    participant_token = token_data.get("access_token") or token_data.get("token")
    assert participant_token is not None
    assert (token_data.get("expires_in_seconds") or token_data.get("expires_in")) > 0

    # Step 8b: Participant accesses portal with token ONLY (no production staff auth header)
    res_portal_view = client.get(
        f"/api/v1/participants/{participant_id}/portal-access?token={participant_token}"
    )
    assert res_portal_view.status_code == 200, res_portal_view.text
    portal_part = res_portal_view.json()
    assert portal_part["display_name"] == "Dr. Miriam Kalu (fictional)"

    # Step 8c: Participant inspects their 15 consent choices with signed token
    res_portal_consents = client.get(
        f"/api/v1/participants/{participant_id}/consent-records?token={participant_token}"
    )
    assert res_portal_consents.status_code == 200, res_portal_consents.text
    portal_consents = res_portal_consents.json()["items"]
    assert len(portal_consents) == 1
    choices_map = {c["category"]: c["choice"] for c in portal_consents[0]["choices"]}
    assert choices_map["interview_recording"] == "agreed"
    assert choices_map["voice_cloning"] == "declined"
    assert choices_map["promotional_clips"] == "not_discussed"

    # Step 8d: Participant submits a clarification / concern request via portal
    res_clarification = client.post(
        f"/api/v1/participants/{participant_id}/clarification-requests?token={participant_token}",
        json={
            "category": "promotional_clips",
            "concern": "I would like to review the proposed social media teaser edit before any festival announcements.",
        },
    )
    assert res_clarification.status_code == 201, res_clarification.text
    clarification_res = res_clarification.json()
    assert clarification_res["status"] == "received"
    task_id = uuid.UUID(clarification_res["task_id"])

    # Verify actionable care task was created in PostgreSQL
    task = db.get(Task, task_id)
    assert task is not None
    assert task.task_type == "participant_follow_up"
    assert task.priority == "high"
    assert "Clarification Request" in task.title

    # Step 8e: Verify immutable audit trail preserves all operations
    res_timeline = client.get(
        f"/api/v1/projects/{pid_str}/timeline?limit=100",
        headers=auth_headers(producer),
    )
    assert res_timeline.status_code == 200
    timeline_items = res_timeline.json()["items"]
    timeline_actions = [e["action"] for e in timeline_items]

    # Verify critical sequence is logged in append-only audit trail
    assert "participant.created" in timeline_actions
    assert "consent_record.created" in timeline_actions
    assert "consent_record.confirmed" in timeline_actions
    assert "proposed_use.created" in timeline_actions
    assert "proposed_use.analysed" in timeline_actions
    assert "review.human_decision" in timeline_actions
    assert "communication.draft_created" in timeline_actions
    assert "communication.approved" in timeline_actions
    assert "communication.send_attempted" in timeline_actions
    assert "participant.clarification_requested" in timeline_actions

    # Direct database audit table verification
    audit_events = db.execute(
        select(AuditEvent).where(AuditEvent.project_id == pid)
    ).scalars().all()
    assert len(audit_events) >= 10
    actor_types = {e.actor_type for e in audit_events}
    assert "user" in actor_types
    assert "system" in actor_types
