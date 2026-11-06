"""Analytics domain service — live, high-performance PostgreSQL aggregations.

Enforces:
- Strict multi-tenant isolation via project membership.
- Distinction between discussion coverage, approval rate, and resolution rate.
- Silence / missing records as unresolved.
- Live database queries with no mutation of state.
"""
from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, desc, func, or_, select, text
from sqlalchemy.orm import Session

from app.analytics.permissions import get_authorized_project_ids
from app.analytics.schemas import (
    AdvisoryAnalyticsOut,
    AnalyticsOverviewOut,
    AnalyticsScopeMetadata,
    CategoryMetricDetail,
    ConsentAnalyticsOut,
    DateRangeMetadata,
    OperationsAnalyticsOut,
    ProjectAnalyticsSummary,
    ReviewAnalyticsOut,
    TrendDataPoint,
    TrendsAnalyticsOut,
    WithdrawalAnalyticsOut,
)
from app.core.choices import CONSENT_CATEGORIES
from app.models import (
    AgentRun,
    AuditEvent,
    ConsentChoice,
    ConsentRecord,
    Participant,
    Project,
    ProposedUse,
    Review,
    Task,
    User,
)


def _build_scope_metadata(
    db: Session,
    authorized_project_ids: list[uuid.UUID],
    single_project_id: uuid.UUID | None,
) -> AnalyticsScopeMetadata:
    if single_project_id and len(authorized_project_ids) == 1:
        proj = db.get(Project, single_project_id)
        title = proj.title if proj else None
        return AnalyticsScopeMetadata(
            project_id=single_project_id,
            project_title=title,
            authorized_projects_count=1,
        )
    return AnalyticsScopeMetadata(
        project_id=None,
        project_title=None,
        authorized_projects_count=len(authorized_project_ids),
    )


def get_analytics_overview(
    db: Session,
    user: User,
    *,
    project_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> AnalyticsOverviewOut:
    """Compute high-level executive and operational KPIs."""
    authorized_ids = get_authorized_project_ids(db, user, project_id)
    scope = _build_scope_metadata(db, authorized_ids, project_id)
    period = DateRangeMetadata(start_date=start_date, end_date=end_date)
    now = datetime.now(UTC)

    if not authorized_ids:
        return AnalyticsOverviewOut(
            period=period,
            scope=scope,
            generated_at=now,
            total_projects=0,
            total_participants=0,
            active_participants=0,
            withdrawn_participants=0,
            discussion_coverage=0.0,
            approval_rate=0.0,
            resolution_rate=0.0,
            unresolved_categories=0,
            pending_human_reviews=0,
            completed_reviews=0,
            withdrawal_requests=0,
            urgent_care_tasks=0,
            open_care_tasks=0,
            overdue_tasks=0,
            avg_review_turnaround_hours=None,
        )

    # 1. Projects count
    total_projects = len(authorized_ids)

    # 2. Participants count & status
    part_stmt = select(
        func.count(Participant.id).label("total"),
        func.count(case((Participant.participant_status == "active", 1))).label("active"),
        func.count(case((Participant.participant_status == "withdrawn", 1))).label("withdrawn"),
    ).where(Participant.project_id.in_(authorized_ids))

    if start_date:
        part_stmt = part_stmt.where(Participant.created_at >= start_date)
    if end_date:
        part_stmt = part_stmt.where(Participant.created_at <= end_date)

    part_res = db.execute(part_stmt).one()
    total_participants = part_res.total or 0
    active_participants = part_res.active or 0
    withdrawn_participants = part_res.withdrawn or 0

    # 3. Consent Rates (using latest confirmed consent record per participant)
    consent_rates = get_consent_analytics(db, user, project_id=project_id, start_date=start_date, end_date=end_date)

    # 4. Human Reviews
    rev_stmt = select(
        func.count(case((Review.review_status == "pending", 1))).label("pending"),
        func.count(case((Review.review_status == "completed", 1))).label("completed"),
    ).where(
        Review.project_id.in_(authorized_ids),
        Review.reviewer_type == "human",
    )
    if start_date:
        rev_stmt = rev_stmt.where(Review.created_at >= start_date)
    if end_date:
        rev_stmt = rev_stmt.where(Review.created_at <= end_date)

    rev_res = db.execute(rev_stmt).one()
    pending_human_reviews = rev_res.pending or 0
    completed_reviews = rev_res.completed or 0

    # 5. Average Review Turnaround
    turnaround_stmt = select(
        Review.created_at,
        Review.decided_at,
    ).where(
        Review.project_id.in_(authorized_ids),
        Review.reviewer_type == "human",
        Review.decided_at.is_not(None),
    )
    turnaround_rows = db.execute(turnaround_stmt).all()
    durations = [
        (r.decided_at - r.created_at).total_seconds() / 3600.0
        for r in turnaround_rows
        if r.decided_at and r.created_at and r.decided_at >= r.created_at
    ]
    avg_turnaround = round(statistics.mean(durations), 2) if durations else None

    # 6. Tasks & Operations
    task_stmt = select(
        func.count(case((and_(Task.priority == "urgent", Task.status.in_(["open", "in_progress", "blocked"])), 1))).label("urgent"),
        func.count(case((Task.status.in_(["open", "in_progress", "blocked"]), 1))).label("open_tasks"),
        func.count(case((and_(Task.due_at.is_not(None), Task.due_at < now, Task.status.in_(["open", "in_progress", "blocked"])), 1))).label("overdue"),
    ).where(Task.project_id.in_(authorized_ids))

    task_res = db.execute(task_stmt).one()
    urgent_care_tasks = task_res.urgent or 0
    open_care_tasks = task_res.open_tasks or 0
    overdue_tasks = task_res.overdue or 0

    # 7. Withdrawal Requests
    # Counted from audit_events (participant.withdrawal_requested) OR tasks with withdrawal intent
    audit_withdraw_stmt = select(func.count(AuditEvent.id)).where(
        AuditEvent.project_id.in_(authorized_ids),
        AuditEvent.action == "participant.withdrawal_requested",
    )
    if start_date:
        audit_withdraw_stmt = audit_withdraw_stmt.where(AuditEvent.timestamp >= start_date)
    if end_date:
        audit_withdraw_stmt = audit_withdraw_stmt.where(AuditEvent.timestamp <= end_date)

    withdrawal_requests = db.execute(audit_withdraw_stmt).scalar() or 0

    return AnalyticsOverviewOut(
        period=period,
        scope=scope,
        generated_at=now,
        total_projects=total_projects,
        total_participants=total_participants,
        active_participants=active_participants,
        withdrawn_participants=withdrawn_participants,
        discussion_coverage=consent_rates.discussion_coverage,
        approval_rate=consent_rates.approval_rate,
        resolution_rate=consent_rates.resolution_rate,
        unresolved_categories=consent_rates.unresolved_categories_count,
        pending_human_reviews=pending_human_reviews,
        completed_reviews=completed_reviews,
        withdrawal_requests=withdrawal_requests,
        urgent_care_tasks=urgent_care_tasks,
        open_care_tasks=open_care_tasks,
        overdue_tasks=overdue_tasks,
        avg_review_turnaround_hours=avg_turnaround,
    )


def get_consent_analytics(
    db: Session,
    user: User,
    *,
    project_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    category_filter: str | None = None,
) -> ConsentAnalyticsOut:
    """Compute detailed 15-category consent breakdown and coverage metrics."""
    authorized_ids = get_authorized_project_ids(db, user, project_id)
    scope = _build_scope_metadata(db, authorized_ids, project_id)
    period = DateRangeMetadata(start_date=start_date, end_date=end_date)

    if not authorized_ids:
        return ConsentAnalyticsOut(
            period=period,
            scope=scope,
            total_participants=0,
            total_applicable_choices=0,
            agreed_choices=0,
            declined_choices=0,
            needs_clarification_choices=0,
            not_discussed_choices=0,
            awaiting_confirmation_choices=0,
            explained_choices=0,
            discussion_coverage=0.0,
            approval_rate=0.0,
            resolution_rate=0.0,
            unresolved_categories_count=0,
            categories=[],
        )

    # Get active participants count
    part_stmt = select(func.count(Participant.id)).where(
        Participant.project_id.in_(authorized_ids),
        Participant.participant_status == "active",
    )
    active_participants_count = db.execute(part_stmt).scalar() or 0

    # Subquery: Latest confirmed consent record per participant
    latest_rec_subq = (
        select(
            ConsentRecord.id.label("consent_record_id"),
            ConsentRecord.participant_id,
            func.row_number().over(
                partition_by=ConsentRecord.participant_id,
                order_by=desc(ConsentRecord.version_number),
            ).label("rn"),
        )
        .where(
            ConsentRecord.project_id.in_(authorized_ids),
            ConsentRecord.record_status == "confirmed",
        )
        .subquery()
    )

    # Choices from the latest confirmed record
    choice_stmt = (
        select(
            ConsentChoice.category,
            func.count(case((ConsentChoice.choice == "agreed", 1))).label("agreed"),
            func.count(case((ConsentChoice.choice == "declined", 1))).label("declined"),
            func.count(case((ConsentChoice.choice == "needs_clarification", 1))).label("needs_clarification"),
            func.count(case((ConsentChoice.choice == "not_discussed", 1))).label("not_discussed"),
            func.count(case((ConsentChoice.choice == "awaiting_confirmation", 1))).label("awaiting_confirmation"),
            func.count(case((ConsentChoice.choice == "explained", 1))).label("explained"),
        )
        .join(latest_rec_subq, ConsentChoice.consent_record_id == latest_rec_subq.c.consent_record_id)
        .where(latest_rec_subq.c.rn == 1)
        .group_by(ConsentChoice.category)
    )

    choice_rows = {row.category: row for row in db.execute(choice_stmt).all()}

    category_details: list[CategoryMetricDetail] = []
    tot_agreed = 0
    tot_declined = 0
    tot_clarif = 0
    tot_not_disc = 0
    tot_await = 0
    tot_explained = 0

    categories_to_evaluate = (
        [category_filter] if category_filter and category_filter in CONSENT_CATEGORIES else list(CONSENT_CATEGORIES)
    )

    for cat in categories_to_evaluate:
        row = choice_rows.get(cat)
        agreed = getattr(row, "agreed", 0) or 0
        declined = getattr(row, "declined", 0) or 0
        clarif = getattr(row, "needs_clarification", 0) or 0
        not_disc_recorded = getattr(row, "not_discussed", 0) or 0
        await_conf = getattr(row, "awaiting_confirmation", 0) or 0
        explained = getattr(row, "explained", 0) or 0

        # Any active participant without this category choice is mathematically 'not_discussed'
        recorded_total = agreed + declined + clarif + not_disc_recorded + await_conf + explained
        missing_count = max(0, active_participants_count - recorded_total)
        effective_not_discussed = not_disc_recorded + missing_count

        total_applicable = active_participants_count
        disc_cov = round(
            ((agreed + declined + clarif + await_conf + explained) / total_applicable * 100.0), 2
        ) if total_applicable > 0 else 0.0

        app_rate = round((agreed / total_applicable * 100.0), 2) if total_applicable > 0 else 0.0
        res_rate = round(((agreed + declined) / total_applicable * 100.0), 2) if total_applicable > 0 else 0.0

        category_details.append(
            CategoryMetricDetail(
                category=cat,
                total_applicable=total_applicable,
                agreed=agreed,
                declined=declined,
                needs_clarification=clarif,
                not_discussed=effective_not_discussed,
                awaiting_confirmation=await_conf,
                explained=explained,
                discussion_coverage=disc_cov,
                approval_rate=app_rate,
                resolution_rate=res_rate,
            )
        )

        tot_agreed += agreed
        tot_declined += declined
        tot_clarif += clarif
        tot_not_disc += effective_not_discussed
        tot_await += await_conf
        tot_explained += explained

    total_applicable_choices = active_participants_count * len(categories_to_evaluate)
    total_discussed_choices = tot_agreed + tot_declined + tot_clarif + tot_await + tot_explained

    overall_disc_coverage = (
        round((total_discussed_choices / total_applicable_choices * 100.0), 2)
        if total_applicable_choices > 0
        else 0.0
    )
    overall_approval_rate = (
        round((tot_agreed / total_applicable_choices * 100.0), 2)
        if total_applicable_choices > 0
        else 0.0
    )
    overall_resolution_rate = (
        round(((tot_agreed + tot_declined) / total_applicable_choices * 100.0), 2)
        if total_applicable_choices > 0
        else 0.0
    )
    unresolved_categories = total_applicable_choices - (tot_agreed + tot_declined)

    return ConsentAnalyticsOut(
        period=period,
        scope=scope,
        total_participants=active_participants_count,
        total_applicable_choices=total_applicable_choices,
        agreed_choices=tot_agreed,
        declined_choices=tot_declined,
        needs_clarification_choices=tot_clarif,
        not_discussed_choices=tot_not_disc,
        awaiting_confirmation_choices=tot_await,
        explained_choices=tot_explained,
        discussion_coverage=overall_disc_coverage,
        approval_rate=overall_approval_rate,
        resolution_rate=overall_resolution_rate,
        unresolved_categories_count=unresolved_categories,
        categories=category_details,
    )


def get_project_analytics_list(
    db: Session,
    user: User,
) -> list[ProjectAnalyticsSummary]:
    """Retrieve operational summaries across all projects authorized for this user."""
    authorized_ids = get_authorized_project_ids(db, user)
    if not authorized_ids:
        return []

    summaries: list[ProjectAnalyticsSummary] = []
    projects = db.execute(
        select(Project).where(Project.id.in_(authorized_ids)).order_by(Project.title)
    ).scalars().all()

    for p in projects:
        # Compute consent rates scoped to single project
        c_out = get_consent_analytics(db, user, project_id=p.id)

        # Count pending reviews
        pend_rev = db.execute(
            select(func.count(Review.id)).where(
                Review.project_id == p.id,
                Review.reviewer_type == "human",
                Review.review_status == "pending",
            )
        ).scalar() or 0

        # Count urgent tasks
        urg_tasks = db.execute(
            select(func.count(Task.id)).where(
                Task.project_id == p.id,
                Task.priority == "urgent",
                Task.status.in_(["open", "in_progress", "blocked"]),
            )
        ).scalar() or 0

        # Count withdrawal requests
        withdr_count = db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.project_id == p.id,
                AuditEvent.action == "participant.withdrawal_requested",
            )
        ).scalar() or 0

        summaries.append(
            ProjectAnalyticsSummary(
                project_id=p.id,
                project_title=p.title,
                project_status=p.status,
                participants_count=c_out.total_participants,
                discussion_coverage=c_out.discussion_coverage,
                approval_rate=c_out.approval_rate,
                resolution_rate=c_out.resolution_rate,
                unresolved_categories=c_out.unresolved_categories_count,
                pending_reviews_count=pend_rev,
                urgent_tasks_count=urg_tasks,
                withdrawal_requests_count=withdr_count,
            )
        )

    return summaries


def get_review_analytics(
    db: Session,
    user: User,
    *,
    project_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ReviewAnalyticsOut:
    """Compute proposed use reviews, decision ratios, and turnaround times."""
    authorized_ids = get_authorized_project_ids(db, user, project_id)
    scope = _build_scope_metadata(db, authorized_ids, project_id)
    period = DateRangeMetadata(start_date=start_date, end_date=end_date)

    if not authorized_ids:
        return ReviewAnalyticsOut(
            period=period,
            scope=scope,
            total_proposed_uses=0,
            pending_reviews=0,
            completed_reviews=0,
            decisions_breakdown={},
            use_type_breakdown={},
            avg_turnaround_hours=None,
            median_turnaround_hours=None,
        )

    # Proposed uses count & use_type distribution
    use_stmt = select(
        ProposedUse.use_type,
        func.count(ProposedUse.id),
    ).where(ProposedUse.project_id.in_(authorized_ids)).group_by(ProposedUse.use_type)

    if start_date:
        use_stmt = use_stmt.where(ProposedUse.created_at >= start_date)
    if end_date:
        use_stmt = use_stmt.where(ProposedUse.created_at <= end_date)

    use_rows = db.execute(use_stmt).all()
    use_types = {r[0]: r[1] for r in use_rows}
    total_proposed_uses = sum(use_types.values())

    # Reviews breakdown
    rev_stmt = select(
        Review.review_status,
        Review.human_decision,
        Review.created_at,
        Review.decided_at,
    ).where(
        Review.project_id.in_(authorized_ids),
        Review.reviewer_type == "human",
    )
    if start_date:
        rev_stmt = rev_stmt.where(Review.created_at >= start_date)
    if end_date:
        rev_stmt = rev_stmt.where(Review.created_at <= end_date)

    reviews = db.execute(rev_stmt).all()
    pending = 0
    completed = 0
    decisions: dict[str, int] = {}
    turnarounds: list[float] = []

    for r in reviews:
        if r.review_status == "pending":
            pending += 1
        elif r.review_status == "completed":
            completed += 1

        if r.human_decision:
            decisions[r.human_decision] = decisions.get(r.human_decision, 0) + 1

        if r.decided_at and r.created_at and r.decided_at >= r.created_at:
            turnarounds.append((r.decided_at - r.created_at).total_seconds() / 3600.0)

    avg_turn = round(statistics.mean(turnarounds), 2) if turnarounds else None
    med_turn = round(statistics.median(turnarounds), 2) if turnarounds else None

    return ReviewAnalyticsOut(
        period=period,
        scope=scope,
        total_proposed_uses=total_proposed_uses,
        pending_reviews=pending,
        completed_reviews=completed,
        decisions_breakdown=decisions,
        use_type_breakdown=use_types,
        avg_turnaround_hours=avg_turn,
        median_turnaround_hours=med_turn,
    )


def get_operations_analytics(
    db: Session,
    user: User,
    *,
    project_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> OperationsAnalyticsOut:
    """Compute participant-care, task backlogs, and operational resolution times."""
    authorized_ids = get_authorized_project_ids(db, user, project_id)
    scope = _build_scope_metadata(db, authorized_ids, project_id)
    period = DateRangeMetadata(start_date=start_date, end_date=end_date)
    now = datetime.now(UTC)

    if not authorized_ids:
        return OperationsAnalyticsOut(
            period=period,
            scope=scope,
            total_tasks=0,
            open_tasks=0,
            in_progress_tasks=0,
            completed_tasks=0,
            urgent_tasks=0,
            high_priority_tasks=0,
            overdue_tasks=0,
            participant_follow_up_tasks=0,
            unresolved_permission_tasks=0,
            avg_resolution_hours=None,
        )

    task_stmt = select(
        Task.status,
        Task.priority,
        Task.task_type,
        Task.due_at,
        Task.created_at,
        Task.completed_at,
    ).where(Task.project_id.in_(authorized_ids))

    if start_date:
        task_stmt = task_stmt.where(Task.created_at >= start_date)
    if end_date:
        task_stmt = task_stmt.where(Task.created_at <= end_date)

    tasks = db.execute(task_stmt).all()
    total = len(tasks)
    open_count = 0
    in_prog_count = 0
    comp_count = 0
    urgent_count = 0
    high_count = 0
    overdue_count = 0
    follow_up_count = 0
    unres_perm_count = 0
    resolution_durations: list[float] = []

    for t in tasks:
        if t.status in ("open", "blocked"):
            open_count += 1
        elif t.status == "in_progress":
            in_prog_count += 1
        elif t.status == "done":
            comp_count += 1

        if t.priority == "urgent" and t.status != "done":
            urgent_count += 1
        elif t.priority == "high" and t.status != "done":
            high_count += 1

        if t.due_at and t.due_at < now and t.status != "done":
            overdue_count += 1

        if t.task_type == "participant_follow_up":
            follow_up_count += 1
        elif t.task_type == "unresolved_permission":
            unres_perm_count += 1

        if t.completed_at and t.created_at and t.completed_at >= t.created_at:
            resolution_durations.append((t.completed_at - t.created_at).total_seconds() / 3600.0)

    avg_res = round(statistics.mean(resolution_durations), 2) if resolution_durations else None

    return OperationsAnalyticsOut(
        period=period,
        scope=scope,
        total_tasks=total,
        open_tasks=open_count,
        in_progress_tasks=in_prog_count,
        completed_tasks=comp_count,
        urgent_tasks=urgent_count,
        high_priority_tasks=high_count,
        overdue_tasks=overdue_count,
        participant_follow_up_tasks=follow_up_count,
        unresolved_permission_tasks=unres_perm_count,
        avg_resolution_hours=avg_res,
    )


def get_withdrawal_analytics(
    db: Session,
    user: User,
    *,
    project_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> WithdrawalAnalyticsOut:
    """Compute participant withdrawal requests, active alerts, and resolution times."""
    authorized_ids = get_authorized_project_ids(db, user, project_id)
    scope = _build_scope_metadata(db, authorized_ids, project_id)
    period = DateRangeMetadata(start_date=start_date, end_date=end_date)

    if not authorized_ids:
        return WithdrawalAnalyticsOut(
            period=period,
            scope=scope,
            total_withdrawal_requests=0,
            active_withdrawals_in_period=0,
            pending_care_tasks=0,
            resolved_care_tasks=0,
            avg_resolution_hours=None,
            recent_withdrawal_events=[],
        )

    # 1. Total withdrawal audit events
    audit_stmt = select(AuditEvent).where(
        AuditEvent.project_id.in_(authorized_ids),
        AuditEvent.action == "participant.withdrawal_requested",
    ).order_by(desc(AuditEvent.timestamp))

    if start_date:
        audit_stmt = audit_stmt.where(AuditEvent.timestamp >= start_date)
    if end_date:
        audit_stmt = audit_stmt.where(AuditEvent.timestamp <= end_date)

    audit_rows = db.execute(audit_stmt).scalars().all()
    total_withdrawals = len(audit_rows)

    # 2. Associated urgent follow-up tasks
    task_stmt = select(Task).where(
        Task.project_id.in_(authorized_ids),
        Task.task_type == "participant_follow_up",
        or_(Task.title.ilike("%WITHDRAWAL%"), Task.description.ilike("%withdraw%")),
    )
    withdrawal_tasks = db.execute(task_stmt).scalars().all()
    pending_tasks = sum(1 for t in withdrawal_tasks if t.status != "done")
    resolved_tasks = sum(1 for t in withdrawal_tasks if t.status == "done")

    task_durations = [
        (t.completed_at - t.created_at).total_seconds() / 3600.0
        for t in withdrawal_tasks
        if t.completed_at and t.created_at and t.completed_at >= t.created_at
    ]
    avg_res = round(statistics.mean(task_durations), 2) if task_durations else None

    # Privacy-conscious event logs (no personal contacts, only audit metadata)
    recent_events = [
        {
            "id": str(e.id),
            "project_id": str(e.project_id),
            "participant_id": str(e.participant_id) if e.participant_id else None,
            "timestamp": e.timestamp.isoformat(),
            "action": e.action,
        }
        for e in audit_rows[:15]
    ]

    return WithdrawalAnalyticsOut(
        period=period,
        scope=scope,
        total_withdrawal_requests=total_withdrawals,
        active_withdrawals_in_period=pending_tasks,
        pending_care_tasks=pending_tasks,
        resolved_care_tasks=resolved_tasks,
        avg_resolution_hours=avg_res,
        recent_withdrawal_events=recent_events,
    )


def get_advisory_analytics(
    db: Session,
    user: User,
    *,
    project_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> AdvisoryAnalyticsOut:
    """Compute AI advisory invocation statistics and human decision concordance rate."""
    authorized_ids = get_authorized_project_ids(db, user, project_id)
    scope = _build_scope_metadata(db, authorized_ids, project_id)
    period = DateRangeMetadata(start_date=start_date, end_date=end_date)

    if not authorized_ids:
        return AdvisoryAnalyticsOut(
            period=period,
            scope=scope,
            total_advisory_runs=0,
            runs_by_agent={},
            status_distribution={},
            alignment_rate=None,
            alignment_sample_size=0,
        )

    agent_stmt = select(
        AgentRun.agent_name,
        AgentRun.execution_status,
        AgentRun.proposed_use_id,
        AgentRun.output_data,
    ).where(AgentRun.project_id.in_(authorized_ids))

    if start_date:
        agent_stmt = agent_stmt.where(AgentRun.created_at >= start_date)
    if end_date:
        agent_stmt = agent_stmt.where(AgentRun.created_at <= end_date)

    agent_rows = db.execute(agent_stmt).all()
    total_runs = len(agent_rows)
    runs_by_agent: dict[str, int] = {}
    status_dist: dict[str, int] = {}

    for r in agent_rows:
        runs_by_agent[r.agent_name] = runs_by_agent.get(r.agent_name, 0) + 1
        status_dist[r.execution_status] = status_dist.get(r.execution_status, 0) + 1

    # Alignment calculation: compare human reviews with advisory outputs
    # Join reviews that have human decisions with agent runs on the same proposed use
    rev_stmt = select(
        Review.proposed_use_id,
        Review.human_decision,
    ).where(
        Review.project_id.in_(authorized_ids),
        Review.reviewer_type == "human",
        Review.human_decision.is_not(None),
    )
    reviews_with_decisions = db.execute(rev_stmt).all()
    decision_map = {r.proposed_use_id: r.human_decision for r in reviews_with_decisions if r.proposed_use_id}

    concordant = 0
    comparable_total = 0

    for r in agent_rows:
        if not r.proposed_use_id or r.proposed_use_id not in decision_map:
            continue
        h_dec = decision_map[r.proposed_use_id]
        out_data = r.output_data or {}

        # Heuristic check on structured advisory recommendations
        # (e.g. if agent recommended approval and human approved, or agent flagged concerns and human declined/paused)
        rec = str(out_data.get("recommendation", "")).lower()
        has_concerns = bool(out_data.get("concerns") or out_data.get("flags") or "discuss" in rec or "caution" in rec)

        comparable_total += 1
        if h_dec == "approve" and not has_concerns or h_dec in ("needs_participant_discussion", "decline", "request_changes") and has_concerns:
            concordant += 1

    alignment_rate = round((concordant / comparable_total * 100.0), 2) if comparable_total > 0 else None

    return AdvisoryAnalyticsOut(
        period=period,
        scope=scope,
        total_advisory_runs=total_runs,
        runs_by_agent=runs_by_agent,
        status_distribution=status_dist,
        alignment_rate=alignment_rate,
        alignment_sample_size=comparable_total,
    )


def get_trends_analytics(
    db: Session,
    user: User,
    *,
    project_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    interval: str = "day",
) -> TrendsAnalyticsOut:
    """Aggregate daily/weekly time series across consent, reviews, tasks, and participants."""
    authorized_ids = get_authorized_project_ids(db, user, project_id)
    scope = _build_scope_metadata(db, authorized_ids, project_id)

    # Default to last 30 days if start_date is not specified
    now = datetime.now(UTC)
    effective_start = start_date or (now - timedelta(days=30))
    effective_end = end_date or now
    period = DateRangeMetadata(start_date=effective_start, end_date=effective_end)

    if not authorized_ids:
        return TrendsAnalyticsOut(
            period=period,
            scope=scope,
            interval=interval,
            series=[],
        )

    # Bucket dictionary by date string (YYYY-MM-DD)
    date_buckets: dict[str, TrendDataPoint] = {}
    curr = effective_start.date()
    end_curr = effective_end.date()
    while curr <= end_curr:
        date_str = curr.isoformat()
        date_buckets[date_str] = TrendDataPoint(date=date_str)
        curr += timedelta(days=1)

    # 1. New Participants
    part_q = select(
        func.to_char(Participant.created_at, "YYYY-MM-DD").label("d"),
        func.count(Participant.id),
    ).where(
        Participant.project_id.in_(authorized_ids),
        Participant.created_at >= effective_start,
        Participant.created_at <= effective_end,
    ).group_by(text("d"))

    for d_str, count in db.execute(part_q).all():
        if d_str in date_buckets:
            date_buckets[d_str].new_participants = count

    # 2. Confirmed Consents (audit_events or consent_records)
    consent_q = select(
        func.to_char(ConsentRecord.confirmed_at, "YYYY-MM-DD").label("d"),
        func.count(ConsentRecord.id),
    ).where(
        ConsentRecord.project_id.in_(authorized_ids),
        ConsentRecord.record_status == "confirmed",
        ConsentRecord.confirmed_at.is_not(None),
        ConsentRecord.confirmed_at >= effective_start,
        ConsentRecord.confirmed_at <= effective_end,
    ).group_by(text("d"))

    for d_str, count in db.execute(consent_q).all():
        if d_str in date_buckets:
            date_buckets[d_str].consent_confirmed = count

    # 3. Reviews Decided
    rev_q = select(
        func.to_char(Review.decided_at, "YYYY-MM-DD").label("d"),
        func.count(Review.id),
    ).where(
        Review.project_id.in_(authorized_ids),
        Review.reviewer_type == "human",
        Review.decided_at.is_not(None),
        Review.decided_at >= effective_start,
        Review.decided_at <= effective_end,
    ).group_by(text("d"))

    for d_str, count in db.execute(rev_q).all():
        if d_str in date_buckets:
            date_buckets[d_str].reviews_decided = count

    # 4. Withdrawals Requested
    withdr_q = select(
        func.to_char(AuditEvent.timestamp, "YYYY-MM-DD").label("d"),
        func.count(AuditEvent.id),
    ).where(
        AuditEvent.project_id.in_(authorized_ids),
        AuditEvent.action == "participant.withdrawal_requested",
        AuditEvent.timestamp >= effective_start,
        AuditEvent.timestamp <= effective_end,
    ).group_by(text("d"))

    for d_str, count in db.execute(withdr_q).all():
        if d_str in date_buckets:
            date_buckets[d_str].withdrawals_requested = count

    # 5. Tasks Completed
    task_q = select(
        func.to_char(Task.completed_at, "YYYY-MM-DD").label("d"),
        func.count(Task.id),
    ).where(
        Task.project_id.in_(authorized_ids),
        Task.completed_at.is_not(None),
        Task.completed_at >= effective_start,
        Task.completed_at <= effective_end,
    ).group_by(text("d"))

    for d_str, count in db.execute(task_q).all():
        if d_str in date_buckets:
            date_buckets[d_str].tasks_completed = count

    sorted_series = [date_buckets[k] for k in sorted(date_buckets.keys())]
    return TrendsAnalyticsOut(
        period=period,
        scope=scope,
        interval=interval,
        series=sorted_series,
    )
