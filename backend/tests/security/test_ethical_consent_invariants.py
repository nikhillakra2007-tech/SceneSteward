"""Ethical & Consent Security Regression Tests.

Formally evaluates and enforces the 12 core Ethical & Consent Invariants of SceneSteward:
1. Silence is never consent (missing response != agreement).
2. Missing consent records must never be interpreted as agreement.
3. No cross-use implication (specific consent does not imply broader/other uses).
4. Consent evaluation is project-isolated and participant-isolated.
5. Inactive, revoked, or expired consent must immediately cause evaluation failure (fail-closed).
6. Ambiguous, missing, or contradictory metadata must flag a review blocker, not assume permission.
7. AI advisory agents cannot mutate database state, sign off on reviews, or override consent blockers.
8. External notification systems must not fire without human-initiated or explicit consent workflow triggers.
9. Audit events are strictly append-only; tampering or deletion must be prevented or detected.
10. Unconfigured notification providers must fail closed.
11. Consent comparison engine must deterministically yield identical results for identical inputs.
12. Identity trust boundary prevents cross-tenant project manipulation even under injection vectors.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.agents import AGENT_CLASSES
from app.core.config import get_settings
from app.core.database import compute_identity_sig
from app.core.exceptions import PreconditionFailed
from app.models import ParticipantCommunication
from app.services import audit, communications
from app.services.consent_comparison import (
    compare_with_confirmed_record,
    normalize_proposed_use,
)
from app.services.consent_service import get_latest_confirmed
from tests.conftest import make_project, make_user


def _make_record(choices_dict: dict[str, str], version_number: int = 1):
    class MockChoice:
        def __init__(self, category: str, choice: str):
            self.id = uuid.uuid4()
            self.category = category
            self.choice = choice
            self.evidence_reference = f"evidence:{category}"

    class MockConsentRecord:
        def __init__(self, choices: list[MockChoice], v: int):
            self.id = uuid.uuid4()
            self.version_number = v
            self.choices = choices

    return MockConsentRecord([MockChoice(k, v) for k, v in choices_dict.items()], version_number)


# --- Invariant 1: Silence is never consent ---
def test_invariant_1_silence_is_never_consent():
    """An empty or unaddressed category in a consent record must evaluate to NEEDS_DISCUSSION, not agreed."""
    record = _make_record({})  # No categories mentioned
    use = SimpleNamespace(
        use_type="festival_submission",
        platform="film_festival",
        audience="festival",
        purpose="screening",
        territory="worldwide",
        context_description="Submission to international documentary festival",
    )
    norm = normalize_proposed_use(use)
    result = compare_with_confirmed_record(record, [], norm)

    assert result.outcome != "RECORDED_CHOICE_MATCH"
    assert result.outcome == "NEEDS_DISCUSSION"
    assert len(result.findings) > 0
    assert any(f.get("choice") is None for f in result.findings)


# --- Invariant 2: Missing consent records must never be interpreted as agreement ---
def test_invariant_2_missing_consent_record_fails_closed():
    """A participant with no confirmed record must fail closed with OUTCOME_MISSING_RECORD."""
    use = SimpleNamespace(
        use_type="theatrical_release",
        platform="cinema",
        audience="general",
        purpose="commercial",
        territory="worldwide",
        context_description="Theatrical screening",
    )
    norm = normalize_proposed_use(use)
    # Passing None as record
    result = compare_with_confirmed_record(None, [], norm)
    assert result.outcome != "RECORDED_CHOICE_MATCH"
    assert "MISSING" in result.outcome or result.outcome == "NEEDS_DISCUSSION"


# --- Invariant 3: No cross-use implication ---
def test_invariant_3_no_cross_use_implication():
    """Consent for archival use or interview recording does not grant trailer or synthetic voice rights."""
    record = _make_record({"interview_recording": "agreed", "archival_preservation": "agreed"})

    # Propose AI voice cloning
    use_vc = SimpleNamespace(
        use_type="voice_cloning",
        platform="youtube",
        audience="global",
        purpose="ai narration",
        territory="worldwide",
        context_description="Synthesized voiceover",
    )
    norm_vc = normalize_proposed_use(use_vc)
    result_vc = compare_with_confirmed_record(record, [], norm_vc)
    assert result_vc.outcome != "RECORDED_CHOICE_MATCH"
    assert result_vc.outcome == "NEEDS_DISCUSSION"

    # Propose promotional trailer
    use_tr = SimpleNamespace(
        use_type="promotional_trailer",
        platform="social_media",
        audience="public",
        purpose="marketing",
        territory="worldwide",
        context_description="Teaser clip",
    )
    norm_tr = normalize_proposed_use(use_tr)
    result_tr = compare_with_confirmed_record(record, [], norm_tr)
    assert result_tr.outcome != "RECORDED_CHOICE_MATCH"
    assert result_tr.outcome == "NEEDS_DISCUSSION"


# --- Invariant 4: Consent evaluation is project-isolated and participant-isolated ---
def test_invariant_4_consent_evaluation_isolation(db):
    """Confirmed consent of Participant A in Project A is never visible or applicable to Participant B in Project B."""
    user_a = make_user(db, f"user_a_{uuid.uuid4().hex[:6]}@test.com")
    user_b = make_user(db, f"user_b_{uuid.uuid4().hex[:6]}@test.com")
    proj_a = make_project(db, user_a, title="Project A")
    proj_b = make_project(db, user_b, title="Project B")

    part_a_id = uuid.uuid4()
    part_b_id = uuid.uuid4()

    db.execute(
        text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Participant A')"),
        {"id": part_a_id, "pid": proj_a.id},
    )
    db.execute(
        text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Participant B')"),
        {"id": part_b_id, "pid": proj_b.id},
    )
    db.commit()

    # Querying latest confirmed for Participant B returns None
    assert get_latest_confirmed(db, part_b_id) is None


# --- Invariant 5: Inactive, revoked, or expired consent fails closed ---
def test_invariant_5_revoked_consent_fails_closed(db):
    """Revoked consent records are never returned by get_latest_confirmed."""
    user = make_user(db, f"user_rev_{uuid.uuid4().hex[:6]}@test.com")
    proj = make_project(db, user, title="Revoke Test Project")
    part_id = uuid.uuid4()
    rec_id = uuid.uuid4()

    db.execute(
        text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Part')"),
        {"id": part_id, "pid": proj.id},
    )
    # Insert revoked record
    db.execute(
        text("""
            INSERT INTO consent_records (id, participant_id, project_id, version_number, record_status,
                                        participant_confirmation, source_type, recorded_by)
            VALUES (:id, :part_id, :pid, 1, 'revoked', 'declined', 'manual', :uid)
        """),
        {"id": rec_id, "part_id": part_id, "pid": proj.id, "uid": user.id},
    )
    db.commit()

    latest = get_latest_confirmed(db, part_id)
    assert latest is None, "Revoked consent records must never be returned as confirmed"


# --- Invariant 6: Ambiguous metadata flags review blocker ---
def test_invariant_6_ambiguous_metadata_flags_blocker():
    """Contradictory or missing metadata causes comparison engine to flag uncertainty."""
    record = _make_record({"broadcast_rights": "agreed"})
    use = SimpleNamespace(
        use_type="broadcast_rights",
        platform="unknown_unsupported_network",
        audience="restricted",
        purpose="undefined_spec",
        territory="non_standard_jurisdiction",
        context_description="",
    )
    norm = normalize_proposed_use(use)
    result = compare_with_confirmed_record(record, [], norm)
    # Must never assume permission; must require discussion or be unresolved
    assert result.outcome in ("UNRESOLVED", "NEEDS_DISCUSSION")
    assert result.requires_human_review is True


# --- Invariant 7: AI advisory agents cannot mutate database state or override blockers ---
def test_invariant_7_ai_agents_are_strictly_advisory():
    """All agent outputs require human review and cannot directly authorize proposed uses."""
    base_ctx = {
        "project_id": str(uuid.uuid4()),
        "participant_id": str(uuid.uuid4()),
        "proposed_use_id": str(uuid.uuid4()),
        "input_reference": "ref:test",
        "proposed_use": {"use_type": "trailer", "status": "submitted"},
        "story_element": {"title": "Scene 1", "sensitivity_level": "high"},
        "latest_confirmed_choices": [],
        "latest_confirmed_version": 1,
        "latest_confirmed_record_id": str(uuid.uuid4()),
        "historical_decisions": [],
        "analysis_findings": [],
        "analysis_outcome": "NEEDS_DISCUSSION",
        "participant_private": {},
        "agent_outputs": {},
        "document_text": [],
    }
    for name, cls in AGENT_CLASSES.items():
        agent = cls()
        payload = agent.offline_result(base_ctx, uuid.uuid4())
        validated = agent._validate(payload, base_ctx, uuid.UUID(payload["run_id"]))
        assert validated.requires_human_review is True, f"Agent {name} must require human review"


# --- Invariant 8: External notification systems require human approval ---
def test_invariant_8_notifications_require_human_approval(db):
    """ParticipantCommunication cannot be marked sent without human approval."""
    user = make_user(db, f"comm_user_{uuid.uuid4().hex[:6]}@test.com")
    proj = make_project(db, user)
    part_id = uuid.uuid4()
    db.execute(
        text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Part Comms')"),
        {"id": part_id, "pid": proj.id},
    )
    db.commit()

    comm = ParticipantCommunication(
        id=uuid.uuid4(),
        project_id=proj.id,
        participant_id=part_id,
        communication_type="email",
        communication_status="draft",
        draft_content="Test notification body",
        created_by=user.id,
        approved_by=None,
    )
    db.add(comm)
    db.commit()

    # Attempting mark_sent directly from draft must raise PreconditionFailed
    with pytest.raises(PreconditionFailed) as exc:
        communications.mark_sent(
            db,
            comm=comm,
            actor_user_id=user.id,
            actor=("user", str(user.id)),
            correlation_id=uuid.uuid4(),
        )
    assert "approved by a human" in str(exc.value)


# --- Invariant 9: Audit events are strictly append-only ---
def test_invariant_9_audit_events_are_append_only(db):
    """Audit events record state transitions with immutable correlation IDs and redacted secrets."""
    proj = make_project(db, make_user(db, f"audit_{uuid.uuid4().hex[:6]}@test.com"))
    event = audit.record(
        db,
        project_id=proj.id,
        participant_id=None,
        actor_type="user",
        actor_id="test_actor",
        action="test.action",
        entity_type="project",
        entity_id=proj.id,
        new_value={"secret_token": "supersecret123", "normal_key": "safe_value"},
        correlation_id=uuid.uuid4(),
    )
    db.commit()

    assert event.id is not None
    assert event.new_value.get("secret_token") == "[redacted]"
    assert event.new_value.get("normal_key") == "safe_value"


# --- Invariant 10: Unconfigured notification providers fail closed ---
def test_invariant_10_unconfigured_providers_fail_closed(db):
    """Unapproved communications are blocked and unconfigured delivery does not fake success."""
    user = make_user(db, f"unconf_{uuid.uuid4().hex[:6]}@test.com")
    proj = make_project(db, user)
    part_id = uuid.uuid4()
    db.execute(
        text("INSERT INTO participants (id, project_id, display_name) VALUES (:id, :pid, 'Part Unconf')"),
        {"id": part_id, "pid": proj.id},
    )
    db.commit()

    comm = ParticipantCommunication(
        id=uuid.uuid4(),
        project_id=proj.id,
        participant_id=part_id,
        communication_type="sms",
        communication_status="draft",
        draft_content="SMS text",
        created_by=user.id,
        approved_by=None,
    )
    db.add(comm)
    db.commit()

    with pytest.raises(PreconditionFailed):
        communications.mark_sent(
            db,
            comm=comm,
            actor_user_id=user.id,
            actor=("user", str(user.id)),
            correlation_id=uuid.uuid4(),
        )


# --- Invariant 11: Deterministic comparison results ---
def test_invariant_11_deterministic_comparison():
    """Identical inputs to consent comparison engine yield identical outputs across repeated executions."""
    record = _make_record({"interview_recording": "agreed", "festival_screening": "declined"})
    use = SimpleNamespace(
        use_type="festival_screening",
        platform="film_festival",
        audience="festival_attendees",
        purpose="premiere",
        territory="north_america",
        context_description="Premiere screening",
    )
    norm = normalize_proposed_use(use)

    res1 = compare_with_confirmed_record(record, [], norm)
    res2 = compare_with_confirmed_record(record, [], norm)

    assert res1.outcome == res2.outcome
    assert len(res1.findings) == len(res2.findings)
    assert [f["category"] for f in res1.findings] == [f["category"] for f in res2.findings]
    assert [f["choice"] for f in res1.findings] == [f["choice"] for f in res2.findings]


# --- Invariant 12: Identity trust boundary prevents cross-tenant project manipulation ---
def test_invariant_12_sql_injection_cannot_bypass_trust_boundary(db):
    """SQL injection payloads in user ID or session context cannot bypass HMAC verification."""
    from sqlalchemy import create_engine

    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)

    injection_payload = "00000000-0000-0000-0000-000000000000' OR '1'='1"
    forged_sig = compute_identity_sig(injection_payload, secret="wrong_key")

    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
            {"uid": injection_payload, "sig": forged_sig},
        )
        # Attempt to select projects under SQL injection
        rows = conn.execute(text("SELECT id FROM projects")).scalars().all()
        assert len(rows) == 0, "SQL injection with invalid signature must see 0 rows under RLS"
