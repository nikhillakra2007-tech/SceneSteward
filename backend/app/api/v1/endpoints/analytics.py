"""Analytics API endpoints — operational intelligence, consent coverage, and reporting."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.analytics.export_service import generate_analytics_export
from app.analytics.schemas import (
    AdvisoryAnalyticsOut,
    AnalyticsOverviewOut,
    CategoryMetricDetail,
    ConsentAnalyticsOut,
    ExportRequestIn,
    ExportResponseOut,
    OperationsAnalyticsOut,
    ProjectAnalyticsSummary,
    ReviewAnalyticsOut,
    TrendsAnalyticsOut,
    WithdrawalAnalyticsOut,
)
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
from app.api.dependencies import CurrentUser, DbSession
from app.core.exceptions import ConflictError

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _validate_dates(start_date: datetime | None, end_date: datetime | None) -> None:
    if start_date and end_date and start_date > end_date:
        raise ConflictError("start_date cannot be after end_date")


@router.get("/overview", response_model=AnalyticsOverviewOut)
def analytics_overview(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope analytics to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp (inclusive)")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp (inclusive)")] = None,
) -> AnalyticsOverviewOut:
    """Retrieve high-level portfolio or project-scoped KPIs."""
    _validate_dates(start_date, end_date)
    return get_analytics_overview(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/projects", response_model=list[ProjectAnalyticsSummary])
def projects_analytics_summary(
    db: DbSession,
    user: CurrentUser,
) -> list[ProjectAnalyticsSummary]:
    """Retrieve operational health and consent summaries across all authorized projects."""
    return get_project_analytics_list(db, user)


@router.get("/consent", response_model=ConsentAnalyticsOut)
def consent_analytics(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp")] = None,
    category: Annotated[str | None, Query(description="Filter to a specific canonical consent category")] = None,
) -> ConsentAnalyticsOut:
    """Retrieve consent distribution and 15-category coverage metrics."""
    _validate_dates(start_date, end_date)
    return get_consent_analytics(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        category_filter=category,
    )


@router.get("/consent/categories", response_model=list[CategoryMetricDetail])
def consent_category_breakdown(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp")] = None,
) -> list[CategoryMetricDetail]:
    """Retrieve granular choice breakdowns across all 15 canonical consent categories."""
    _validate_dates(start_date, end_date)
    out = get_consent_analytics(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )
    return out.categories


@router.get("/reviews", response_model=ReviewAnalyticsOut)
def review_analytics(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp")] = None,
) -> ReviewAnalyticsOut:
    """Retrieve proposed-use review queues, decision ratios, and turnaround times."""
    _validate_dates(start_date, end_date)
    return get_review_analytics(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/operations", response_model=OperationsAnalyticsOut)
def operations_analytics(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp")] = None,
) -> OperationsAnalyticsOut:
    """Retrieve operational task health, urgency distribution, and overdue items."""
    _validate_dates(start_date, end_date)
    return get_operations_analytics(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/withdrawals", response_model=WithdrawalAnalyticsOut)
def withdrawal_analytics(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp")] = None,
) -> WithdrawalAnalyticsOut:
    """Retrieve participant withdrawal alerts, pending intervention tasks, and resolution times."""
    _validate_dates(start_date, end_date)
    return get_withdrawal_analytics(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/advisory", response_model=AdvisoryAnalyticsOut)
def advisory_analytics(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp")] = None,
) -> AdvisoryAnalyticsOut:
    """Retrieve AI advisory agent invocations and human decision concordance metrics."""
    _validate_dates(start_date, end_date)
    return get_advisory_analytics(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/trends", response_model=TrendsAnalyticsOut)
def trends_analytics(
    db: DbSession,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID | None, Query(description="Scope to a specific project")] = None,
    start_date: Annotated[datetime | None, Query(description="Earliest ISO timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest ISO timestamp")] = None,
    interval: Annotated[str, Query(pattern="^(day|week|month)$", description="Bucket size")] = "day",
) -> TrendsAnalyticsOut:
    """Retrieve chronological event series for consent, reviews, tasks, and withdrawals."""
    _validate_dates(start_date, end_date)
    return get_trends_analytics(
        db,
        user,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
    )


@router.post("/exports", response_model=ExportResponseOut)
def export_analytics(
    payload: ExportRequestIn,
    db: DbSession,
    user: CurrentUser,
) -> ExportResponseOut:
    """Generate and return an export report in CSV or JSON format."""
    _validate_dates(payload.start_date, payload.end_date)
    return generate_analytics_export(db, user, payload)
