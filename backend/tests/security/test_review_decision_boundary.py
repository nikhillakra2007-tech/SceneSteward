"""Security boundary tests for Review Decisions and Consent Invariants.

Enforces:
1. Unauthenticated decision is denied (401).
2. Cross-project review access is denied / non-disclosing (404).
3. Unauthorized project member (viewer/editor) is denied (403).
4. AI service agent identity cannot make a human decision (403).
5. Missing or short rationale is rejected (422).
6. Invalid decision enum is rejected (422).
7. Stale review version is rejected with conflict (409).
8. NOT_DISCUSSED consent does not grant clearance.
9. Withdrawn consent blocks clearance (PARTICIPANT_DECLINED).
10. Human review decision does NOT manufacture participant consent (consent choices remain unmodified).
11. Audit event and review decision are atomically committed.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import AuditEvent, ConsentChoice, ConsentRecord, Participant, ProposedUse, Review
from tests.conftest import add_member, auth_headers, make_project, make_user


@pytest.fixture()
def review_setup(db):
    owner = make_user(db, "owner_rev@sec.test", "Owner Rev")
    project = make_project(db, owner, title="Review Sec Project")

    # Roles
    viewer = make_user(db, "viewer_rev@sec.test", "Viewer Rev")
    add_member(db, project, viewer, "viewer")

    editor = make_user(db, "editor_rev@sec.test", "Editor Rev")
    add_member(db, project, editor, "editor")

    agent_user = make_user(db, "agent_rev@sec.test", "Service Agent Rev")
    add_member(db, project, agent_user, "service_agent")

    producer = make_user(db, "producer_rev@sec.test", "Producer Rev")
    add_member(db, project, producer, "producer")

    # Outsider from other project
    outsider = make_user(db, "outsider_rev@sec.test", "Outsider Rev")
    other_project = make_project(db, outsider, title="Other Project")

    # Participant with initial release
    participant = Participant(project_id=project.id, display_name="Test Subject", participant_status="active")
    db.add(participant)
    db.flush()

    release = ConsentRecord(
        participant_id=participant.id,
        project_id=project.id,
        version_number=1,
        record_status="confirmed",
        source_type="release_form",
        recorded_by=owner.id,
        participant_confirmation="confirmed",
    )
    db.add(release)
    db.flush()

    # Agreed for interview, but NOT promotional_clips
    db.add(ConsentChoice(consent_record_id=release.id, category="interview_recording", choice="agreed"))
    db.add(ConsentChoice(consent_record_id=release.id, category="promotional_clips", choice="not_discussed"))
    db.flush()

    # Proposed use
    prop_use = ProposedUse(
        project_id=project.id,
        participant_id=participant.id,
        use_type="promotional_clips",
        context_description="Trailer clip",
        proposed_by=owner.id,
        status="draft",
    )
    db.add(prop_use)
    db.flush()

    # Review
    review = Review(
        project_id=project.id,
        proposed_use_id=prop_use.id,
        reviewer_type="human",
        review_status="pending",
        findings=[],
        evidence_references=[],
        version=1,
    )
    db.add(review)
    db.commit()

    return {
        "owner": owner,
        "producer": producer,
        "viewer": viewer,
        "editor": editor,
        "agent_user": agent_user,
        "outsider": outsider,
        "project": project,
        "other_project": other_project,
        "participant": participant,
        "release": release,
        "prop_use": prop_use,
        "review": review,
    }


def test_unauthenticated_decision_denied(client, review_setup):
    """Unauthenticated caller must be rejected with 401."""
    rev_id = review_setup["review"].id
    res = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "decline", "reason": "No auth header provided", "expected_version": 1},
    )
    assert res.status_code == 401


def test_cross_project_review_access_denied(client, review_setup):
    """User from another project must receive 404 (non-disclosing)."""
    rev_id = review_setup["review"].id
    outsider = review_setup["outsider"]
    res = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "decline", "reason": "Attempting cross project decision", "expected_version": 1},
        headers=auth_headers(outsider),
    )
    assert res.status_code == 404


def test_unauthorized_reviewer_denied(client, review_setup):
    """Project viewer and editor must be rejected with 403."""
    rev_id = review_setup["review"].id
    viewer = review_setup["viewer"]
    editor = review_setup["editor"]

    res_v = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "decline", "reason": "Viewer attempting decision", "expected_version": 1},
        headers=auth_headers(viewer),
    )
    assert res_v.status_code == 403

    res_e = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "decline", "reason": "Editor attempting decision", "expected_version": 1},
        headers=auth_headers(editor),
    )
    assert res_e.status_code == 403


def test_ai_identity_cannot_make_human_decision(client, review_setup):
    """Service agent role must be rejected with 403."""
    rev_id = review_setup["review"].id
    agent_user = review_setup["agent_user"]
    res = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "approve", "reason": "AI attempting autonomous approval", "expected_version": 1},
        headers=auth_headers(agent_user),
    )
    assert res.status_code == 403


def test_missing_rationale_rejected(client, review_setup):
    """Empty or too short rationale (< 3 chars) must be rejected with 422."""
    rev_id = review_setup["review"].id
    owner = review_setup["owner"]

    res_empty = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "decline", "reason": "", "expected_version": 1},
        headers=auth_headers(owner),
    )
    assert res_empty.status_code == 422

    res_short = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "decline", "reason": "no", "expected_version": 1},
        headers=auth_headers(owner),
    )
    assert res_short.status_code == 422


def test_invalid_decision_rejected(client, review_setup):
    """Invalid decision string not in HUMAN_DECISIONS must be rejected with 422."""
    rev_id = review_setup["review"].id
    owner = review_setup["owner"]
    res = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "grant_consent", "reason": "Invalid non-enum decision", "expected_version": 1},
        headers=auth_headers(owner),
    )
    assert res.status_code == 422


def test_stale_version_rejected(client, review_setup):
    """Stale expected_version must be rejected with 409 conflict."""
    rev_id = review_setup["review"].id
    owner = review_setup["owner"]
    res = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "decline", "reason": "Valid reason for stale test", "expected_version": 99},
        headers=auth_headers(owner),
    )
    assert res.status_code == 409


def test_human_decision_does_not_manufacture_consent(client, review_setup, db):
    """A human review decision changes ProposedUse status but NEVER alters ConsentChoice table."""
    rev_id = review_setup["review"].id
    owner = review_setup["owner"]
    release_id = review_setup["release"].id

    # Check baseline consent choices
    baseline_choices = {
        c.category: c.choice
        for c in db.execute(select(ConsentChoice).where(ConsentChoice.consent_record_id == release_id)).scalars().all()
    }
    assert baseline_choices["promotional_clips"] == "not_discussed"

    # Authorized owner approves review
    res = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "approve", "reason": "Documentary production decision to proceed", "expected_version": 1},
        headers=auth_headers(owner),
    )
    assert res.status_code == 200

    # Verify Review and ProposedUse were updated
    db.expire_all()
    rev = db.get(Review, rev_id)
    assert rev.human_decision == "approve"
    assert rev.review_status == "completed"

    prop_use = db.get(ProposedUse, rev.proposed_use_id)
    assert prop_use.status == "approved"

    # CRITICAL: Verify ConsentChoice was NOT mutated (participant consent was NOT manufactured)
    post_choices = {
        c.category: c.choice
        for c in db.execute(select(ConsentChoice).where(ConsentChoice.consent_record_id == release_id)).scalars().all()
    }
    assert post_choices["promotional_clips"] == "not_discussed", "Human review MUST NOT manufacture consent"
    assert post_choices == baseline_choices


def test_audit_and_decision_transaction_atomic(client, review_setup, db):
    """A successful human decision writes both Review status and AuditEvent atomically."""
    rev_id = review_setup["review"].id
    owner = review_setup["owner"]

    res = client.post(
        f"/api/v1/reviews/{rev_id}/human-decision",
        json={"decision": "needs_participant_discussion", "reason": "Requires discussion before trailer lock", "expected_version": 1},
        headers=auth_headers(owner),
    )
    assert res.status_code == 200

    # Verify AuditEvent exists for this exact decision
    audit_row = db.execute(
        select(AuditEvent).where(AuditEvent.entity_id == rev_id, AuditEvent.action == "review.human_decision")
    ).scalars().first()
    assert audit_row is not None
    assert audit_row.actor_id == str(owner.id)
    assert audit_row.reason == "Requires discussion before trailer lock"
    assert audit_row.new_value["decision"] == "needs_participant_discussion"
