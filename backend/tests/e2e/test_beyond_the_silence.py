"""E2E — 'Beyond the Silence': the canonical acceptance scenario, over HTTP.

Beyond the Silence: Amara Okoro (fictional) agreed to interview recording and
documentary appearance; nothing was said about promotional clips or AI voice
reconstruction. Production submits a proposed use combining both. Expected
outcome: NEEDS_DISCUSSION. No agent or human automation may approve it.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models import (
    AuditEvent,
    ConsentRecord,
    ParticipantCommunication,
    ProposedUseAnalysis,
    Review,
)
from tests.conftest import auth_headers, make_user


@pytest.fixture()
def beyond(client, db):
    owner = make_user(db, "oscar@e2e.test", "Oscar Owner")
    producer = make_user(db, "priya@e2e.test", "Priya Producer")
    director = make_user(db, "dana@e2e.test", "Dana Director")
    editor = make_user(db, "eli@e2e.test", "Eli Editor")
    care = make_user(db, "nora@e2e.test", "Nora Care Lead")
    viewer = make_user(db, "vera@e2e.test", "Vera Viewer")

    r = client.post("/api/v1/projects",
                    json={"title": "Beyond the Silence",
                          "description": "A fictional documentary.",
                          "purpose": "Portrait of community-led river restoration",
                          "themes": ["environment"], "intended_audiences": ["festival"]},
                    headers=auth_headers(owner))
    assert r.status_code == 201
    project = r.json()
    pid = project["id"]
    for user, role in [(producer, "producer"), (director, "director"),
                       (editor, "editor"), (care, "participant_care_lead"), (viewer, "viewer")]:
        _add_member_raw(db, uuid.UUID(pid), user, role, owner)

    r = client.post(f"/api/v1/projects/{pid}/participants",
                    json={"display_name": "Amara Okoro (fictional)",
                          "preferred_language": "en",
                          "accessibility_requirements": {"captions": True},
                          "privacy_preferences": {"no_home_address_filming": True}},
                    headers=auth_headers(owner))
    assert r.status_code == 201
    participant = r.json()

    r = client.post(f"/api/v1/participants/{participant['id']}/consent-records",
                    json={"source_type": "verbal_recorded",
                          "explanation": "Recorded 2026-09-12; confirmed on camera.",
                          "choices": [
                              {"category": "interview_recording", "choice": "agreed",
                               "evidence_reference": "release-form:A-01#interview"},
                              {"category": "documentary_appearance", "choice": "agreed",
                               "evidence_reference": "release-form:A-01#appearance"},
                          ]},
                    headers=auth_headers(owner))
    assert r.status_code == 201
    record = r.json()
    r = client.post(f"/api/v1/consent-records/{record['id']}/confirm",
                    json={"confirmation": "confirmed",
                          "confirmation_evidence": "participant confirmed on camera, 2026-09-12",
                          "expected_version": record["version"]},
                    headers=auth_headers(care))
    assert r.status_code == 200
    assert r.json()["record_status"] == "confirmed"

    r = client.post(f"/api/v1/projects/{pid}/story-elements",
                    json={"title": "The riverbed at dawn", "scene_reference": "SCENE-04",
                          "description": "Amara walks the exposed riverbed; voiceover about the 2019 flood.",
                          "identifying_details": ["voice print", "scar on left hand"],
                          "sensitivity_level": "highly_sensitive"},
                    headers=auth_headers(director))
    assert r.status_code == 201
    element = r.json()

    return {"owner": owner, "producer": producer, "director": director, "editor": editor,
            "care": care, "viewer": viewer, "project_id": pid,
            "participant_id": participant["id"], "record_id": record["id"],
            "element_id": element["id"]}


def _add_member_raw(db, project_id, user, role, inviter):
    from app.models import ProjectMembership
    m = ProjectMembership(project_id=project_id, user_id=user.id, role=role,
                          membership_status="active", invited_by=inviter.id)
    db.add(m)
    db.commit()
    return m


def test_beyond_the_silence_full_flow(client, db, beyond):
    pid = beyond["project_id"]
    participant_id = beyond["participant_id"]
    director = beyond["director"]
    producer = beyond["producer"]

    # 1. Proposed use: promotional trailer with sensitive excerpt + AI voice reconstruction
    r = client.post(f"/api/v1/projects/{pid}/proposed-uses",
                    json={"participant_id": participant_id,
                          "story_element_id": beyond["element_id"],
                          "use_type": "promotional_trailer",
                          "platform": "youtube",
                          "audience": "general public",
                          "purpose": "Festival promotion and publicity",
                          "territory": "worldwide",
                          "context_description": ("Sensitive interview excerpt about the 2019 flood used for "
                                                  "the promotional trailer, plus AI voice reconstruction of "
                                                  "scenes the participant never recorded."),
                          "run_analysis": True},
                    headers=auth_headers(director))
    assert r.status_code == 201, r.text
    use = r.json()
    assert use["status"] == "analysis_complete"

    # 2. Persisted analysis outcome is NEEDS_DISCUSSION
    analysis = db.execute(
        select(ProposedUseAnalysis).where(ProposedUseAnalysis.proposed_use_id == uuid.UUID(use["id"]))
        .order_by(ProposedUseAnalysis.created_at.desc()).limit(1)
    ).scalar_one()
    assert analysis.outcome == "NEEDS_DISCUSSION"
    unsettled = {f["category"] for f in analysis.findings if f.get("choice") is None}
    assert {"promotional_clips", "voice_cloning"} <= unsettled
    agreed = {f["category"] for f in analysis.findings if f.get("choice") == "agreed"}
    assert "interview_recording" in agreed  # evidence-grounded match, never approval

    # 3. Consent record was NOT modified by any of this
    record = db.get(ConsentRecord, uuid.UUID(beyond["record_id"]))
    assert record.record_status == "confirmed"
    assert record.version_number == 1
    assert sorted(c.category for c in record.choices) == ["documentary_appearance", "interview_recording"]

    # 4. Human review created and pending; production coordinator created a follow-up task
    review = db.execute(select(Review).where(Review.proposed_use_id == uuid.UUID(use["id"]))).scalar_one()
    assert review.review_status == "pending"
    tasks = client.get(f"/api/v1/projects/{pid}/tasks?status=open",
                       headers=auth_headers(producer)).json()["items"]
    assert any(t["task_type"] == "unresolved_permission" for t in tasks)
    assert any(t["task_type"] == "review" for t in tasks)

    # 5. All five agent runs succeeded (offline deterministic mode)
    findings = client.get(f"/api/v1/proposed-uses/{use['id']}/agent-findings",
                          headers=auth_headers(producer)).json()
    assert len(findings) == 5
    assert all(f["execution_status"] == "succeeded" for f in findings)
    outcome_by_agent = {f["agent_name"]: (f.get("output_data") or {}).get("result") for f in findings}
    assert all(v == "NEEDS_DISCUSSION" for v in outcome_by_agent.values())

    # 6. A draft participant communication exists and is NOT sent
    draft = db.execute(select(ParticipantCommunication)
                       .where(ParticipantCommunication.participant_id == uuid.UUID(participant_id))).scalars().all()
    assert draft and all(d.communication_status == "draft" for d in draft)
    assert all(d.sent_at is None for d in draft)

    # 7. Timeline preserves the whole chain (audit before/after agents)
    timeline = client.get(f"/api/v1/projects/{pid}/timeline?limit=100",
                          headers=auth_headers(producer)).json()["items"]
    actions = [t["action"] for t in timeline]
    assert "proposed_use.created" in actions
    assert "proposed_use.analysed" in actions
    assert actions.count("agent_run.succeeded") >= 5

    # 8. Human records the decision: participant discussion required
    latest_version = review.version
    r = client.post(f"/api/v1/reviews/{review.id}/human-decision",
                    json={"decision": "needs_participant_discussion",
                          "reason": "Trailer and voice reconstruction were never discussed with Amara.",
                          "expected_version": latest_version},
                    headers=auth_headers(producer))
    assert r.status_code == 200, r.text
    assert r.json()["review_status"] == "completed"

    use_after = client.get(f"/api/v1/proposed-uses/{use['id']}",
                           headers=auth_headers(producer)).json()
    assert use_after["status"] == "awaiting_participant_discussion"

    # 9. A decided review cannot be decided again (immutability of decisions)
    r = client.post(f"/api/v1/reviews/{review.id}/human-decision",
                    json={"decision": "approve", "reason": "changed my mind",
                          "expected_version": r.json()["version"]},
                    headers=auth_headers(producer))
    assert r.status_code in (409, 412)

    # 10. The decision is on the accountability timeline, attributed to a human
    timeline = client.get(f"/api/v1/projects/{pid}/timeline?limit=100",
                          headers=auth_headers(producer)).json()["items"]
    decision_entries = [t for t in timeline if t["action"] == "review.human_decision"]
    assert decision_entries and decision_entries[0]["actor_type"] == "user"

    # 11. Audit rows exist for the critical chain and are append-only
    rows = db.execute(select(AuditEvent).where(AuditEvent.project_id == uuid.UUID(pid))).scalars().all()
    entities = {r.entity_type for r in rows}
    assert {"proposed_use", "review", "consent_record", "agent_run"} <= entities


def test_viewer_cannot_drive_the_flow(client, db, beyond):
    viewer = beyond["viewer"]
    pid = beyond["project_id"]
    r = client.post(f"/api/v1/projects/{pid}/proposed-uses",
                    json={"participant_id": beyond["participant_id"],
                          "use_type": "promotional_trailer",
                          "context_description": "promotional trailer"},
                    headers=auth_headers(viewer))
    assert r.status_code == 403
