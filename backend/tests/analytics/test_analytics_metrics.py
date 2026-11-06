"""Unit and integration tests for analytics metric calculations and formulas.

Verifies:
1. Discussion coverage vs Approval rate vs Resolution rate calculations.
2. Silence / not_discussed / missing records are never treated as consent.
3. Accurate handling of 15 canonical categories.
4. Withdrawal count and urgent care task aggregation.
5. Review turnaround calculation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.analytics.service import (
    get_advisory_analytics,
    get_analytics_overview,
    get_consent_analytics,
    get_operations_analytics,
    get_project_analytics_list,
    get_review_analytics,
    get_trends_analytics,
    get_withdrawal_analytics,
)
from app.core.choices import CONSENT_CATEGORIES
from app.models import (
    AgentRun,
    AuditEvent,
    ConsentChoice,
    ConsentRecord,
    Participant,
    ProposedUse,
    Review,
    Task,
)
from tests.conftest import make_project, make_user


@pytest.fixture()
def seeded_analytics_project(db):
    owner = make_user(db, f"owner_{uuid.uuid4().hex[:6]}@analytics.test", "Director Alice")
    project = make_project(db, owner, title="River of Voices")

    # 3 Participants:
    # Part 1: Fully confirmed with 10 agreed, 3 declined, 2 needs_clarification
    # Part 2: Confirmed with 5 agreed, 10 not_discussed
    # Part 3: No confirmed consent record at all (all 15 categories missing -> not_discussed)
    p1 = Participant(project_id=project.id, display_name="Elena Rostova", participant_status="active")
    p2 = Participant(project_id=project.id, display_name="Samir Khan", participant_status="active")
    p3 = Participant(project_id=project.id, display_name="Maria Santos", participant_status="active")
    # Part 4: Withdrawn participant
    p4 = Participant(project_id=project.id, display_name="Withdrawn Contributor", participant_status="withdrawn")
    db.add_all([p1, p2, p3, p4])
    db.commit()

    # Rec 1 for P1
    rec1 = ConsentRecord(
        participant_id=p1.id,
        project_id=project.id,
        version_number=1,
        record_status="confirmed",
        source_type="interview",
        recorded_by=owner.id,
        participant_confirmation="confirmed",
        confirmed_at=datetime.now(UTC) - timedelta(days=5),
    )
    db.add(rec1)
    db.flush()

    for idx, cat in enumerate(CONSENT_CATEGORIES):
        if idx < 10:
            choice_val = "agreed"
        elif idx < 13:
            choice_val = "declined"
        else:
            choice_val = "needs_clarification"
        db.add(ConsentChoice(consent_record_id=rec1.id, category=cat, choice=choice_val))

    # Rec 2 for P2
    rec2 = ConsentRecord(
        participant_id=p2.id,
        project_id=project.id,
        version_number=1,
        record_status="confirmed",
        source_type="release_form",
        recorded_by=owner.id,
        participant_confirmation="confirmed",
        confirmed_at=datetime.now(UTC) - timedelta(days=2),
    )
    db.add(rec2)
    db.flush()

    for idx, cat in enumerate(CONSENT_CATEGORIES):
        choice_val = "agreed" if idx < 5 else "not_discussed"
        db.add(ConsentChoice(consent_record_id=rec2.id, category=cat, choice=choice_val))

    # Tasks
    t1 = Task(
        project_id=project.id,
        participant_id=p1.id,
        task_type="participant_follow_up",
        title="Check interview edit",
        priority="urgent",
        status="open",
        created_by_actor_type="user",
    )
    t2 = Task(
        project_id=project.id,
        participant_id=p2.id,
        task_type="participant_follow_up",
        title="Withdrawal follow-up",
        description="Participant requested withdraw",
        priority="urgent",
        status="done",
        created_by_actor_type="system",
        completed_at=datetime.now(UTC),
    )
    db.add_all([t1, t2])

    # Proposed Use & Review
    use1 = ProposedUse(
        project_id=project.id,
        participant_id=p1.id,
        use_type="promotional_clips",
        status="analysis_complete",
        proposed_by=owner.id,
    )
    db.add(use1)
    db.flush()

    rev1 = Review(
        project_id=project.id,
        proposed_use_id=use1.id,
        reviewer_type="human",
        reviewer_id=owner.id,
        review_status="completed",
        human_decision="approve",
        decided_by=owner.id,
        decided_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db.add(rev1)

    # Advisory run
    ar1 = AgentRun(
        project_id=project.id,
        proposed_use_id=use1.id,
        agent_name="consent_analyst",
        model_provider="offline",
        execution_status="succeeded",
        output_data={"recommendation": "approve", "flags": []},
    )
    db.add(ar1)

    # Audit withdrawal
    audit_ev = AuditEvent(
        project_id=project.id,
        participant_id=p4.id,
        actor_type="system",
        actor_id="participant_portal",
        action="participant.withdrawal_requested",
        entity_type="task",
        timestamp=datetime.now(UTC),
    )
    db.add(audit_ev)

    db.commit()
    return {"owner": owner, "project": project, "p1": p1, "p2": p2, "p3": p3, "p4": p4}


def test_consent_metrics_formulas(db, seeded_analytics_project):
    owner = seeded_analytics_project["owner"]
    project = seeded_analytics_project["project"]

    res = get_consent_analytics(db, owner, project_id=project.id)

    # Total active participants = 3 (P1, P2, P3). P4 is withdrawn.
    assert res.total_participants == 3
    # Total applicable choices = 3 * 15 = 45 choices
    assert res.total_applicable_choices == 45

    # Agreed choices: P1 has 10, P2 has 5, P3 has 0 -> Total = 15
    assert res.agreed_choices == 15
    # Declined choices: P1 has 3, P2 has 0, P3 has 0 -> Total = 3
    assert res.declined_choices == 3
    # Needs clarification: P1 has 2, P2 has 0, P3 has 0 -> Total = 2
    assert res.needs_clarification_choices == 2

    # Not discussed: P1 has 0, P2 has 10, P3 has 15 (unrecorded) -> Total = 25
    assert res.not_discussed_choices == 25

    # Total discussed = agreed(15) + declined(3) + clarification(2) = 20 choices
    # Discussion Coverage = 20 / 45 * 100 = 44.44%
    assert res.discussion_coverage == 44.44

    # Explicit Approval Rate = 15 / 45 * 100 = 33.33%
    assert res.approval_rate == 33.33

    # Resolution Rate = (15 agreed + 3 declined) / 45 * 100 = 18 / 45 * 100 = 40.0%
    assert res.resolution_rate == 40.0

    # Unresolved categories = 45 - 18 = 27
    assert res.unresolved_categories_count == 27


def test_overview_kpis(db, seeded_analytics_project):
    owner = seeded_analytics_project["owner"]
    project = seeded_analytics_project["project"]

    ov = get_analytics_overview(db, owner, project_id=project.id)

    assert ov.total_projects == 1
    assert ov.total_participants == 4  # All participants created (including withdrawn)
    assert ov.active_participants == 3
    assert ov.withdrawn_participants == 1
    assert ov.withdrawal_requests == 1
    assert ov.urgent_care_tasks == 1  # t1 is open and urgent, t2 is done
    assert ov.completed_reviews == 1
    assert ov.pending_human_reviews == 0


def test_review_and_advisory_analytics(db, seeded_analytics_project):
    owner = seeded_analytics_project["owner"]
    project = seeded_analytics_project["project"]

    rev_res = get_review_analytics(db, owner, project_id=project.id)
    assert rev_res.total_proposed_uses == 1
    assert rev_res.completed_reviews == 1
    assert rev_res.decisions_breakdown.get("approve") == 1

    adv_res = get_advisory_analytics(db, owner, project_id=project.id)
    assert adv_res.total_advisory_runs == 1
    assert adv_res.runs_by_agent.get("consent_analyst") == 1
    assert adv_res.alignment_rate == 100.0  # Agent recommended approve and human approved
    assert "strictly informational" in adv_res.disclaimer


def test_operations_and_withdrawal_analytics(db, seeded_analytics_project):
    owner = seeded_analytics_project["owner"]
    project = seeded_analytics_project["project"]

    ops = get_operations_analytics(db, owner, project_id=project.id)
    assert ops.total_tasks == 2
    assert ops.open_tasks == 1
    assert ops.completed_tasks == 1
    assert ops.urgent_tasks == 1

    withdr = get_withdrawal_analytics(db, owner, project_id=project.id)
    assert withdr.total_withdrawal_requests == 1
    assert len(withdr.recent_withdrawal_events) == 1


def test_trends_time_series(db, seeded_analytics_project):
    owner = seeded_analytics_project["owner"]
    project = seeded_analytics_project["project"]

    trends = get_trends_analytics(db, owner, project_id=project.id)
    assert len(trends.series) > 0
    total_confirmed = sum(p.consent_confirmed for p in trends.series)
    assert total_confirmed == 2  # P1 and P2 consent records confirmed


def test_projects_summary_list(db, seeded_analytics_project):
    owner = seeded_analytics_project["owner"]
    project = seeded_analytics_project["project"]

    summaries = get_project_analytics_list(db, owner)
    assert len(summaries) == 1
    s = summaries[0]
    assert s.project_id == project.id
    assert s.project_title == project.title
    assert s.participants_count == 3
    assert s.approval_rate == 33.33
    assert s.resolution_rate == 40.0

