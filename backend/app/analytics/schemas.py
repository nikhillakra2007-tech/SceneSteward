"""Pydantic V2 schemas for SceneSteward Analytics subsystem.

Strictly defines request filters, metric values, breakdown structures,
and export payloads.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalyticsFilterParams(BaseModel):
    """Common filter parameters for analytics queries."""
    project_id: uuid.UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    category: str | None = None
    interval: str = Field(default="day", pattern="^(day|week|month)$")


class DateRangeMetadata(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    timezone: str = "UTC"


class AnalyticsScopeMetadata(BaseModel):
    project_id: uuid.UUID | None = None
    project_title: str | None = None
    authorized_projects_count: int = 1


class CategoryMetricDetail(BaseModel):
    category: str
    total_applicable: int
    agreed: int
    declined: int
    needs_clarification: int
    not_discussed: int
    awaiting_confirmation: int
    explained: int
    discussion_coverage: float  # (agreed + declined + clarification + explained + awaiting) / total * 100
    approval_rate: float        # agreed / total * 100
    resolution_rate: float      # (agreed + declined) / total * 100


class ProjectAnalyticsSummary(BaseModel):
    project_id: uuid.UUID
    project_title: str
    project_status: str
    participants_count: int
    discussion_coverage: float
    approval_rate: float
    resolution_rate: float
    unresolved_categories: int
    pending_reviews_count: int
    urgent_tasks_count: int
    withdrawal_requests_count: int


class AnalyticsOverviewOut(BaseModel):
    period: DateRangeMetadata
    scope: AnalyticsScopeMetadata
    generated_at: datetime
    # Core KPIs
    total_projects: int
    total_participants: int
    active_participants: int
    withdrawn_participants: int
    discussion_coverage: float
    approval_rate: float
    resolution_rate: float
    unresolved_categories: int
    pending_human_reviews: int
    completed_reviews: int
    withdrawal_requests: int
    urgent_care_tasks: int
    open_care_tasks: int
    overdue_tasks: int
    avg_review_turnaround_hours: float | None = None
    data_completeness: str = "complete"


class ConsentAnalyticsOut(BaseModel):
    period: DateRangeMetadata
    scope: AnalyticsScopeMetadata
    total_participants: int
    total_applicable_choices: int
    agreed_choices: int
    declined_choices: int
    needs_clarification_choices: int
    not_discussed_choices: int
    awaiting_confirmation_choices: int
    explained_choices: int
    discussion_coverage: float
    approval_rate: float
    resolution_rate: float
    unresolved_categories_count: int
    categories: list[CategoryMetricDetail]


class ReviewAnalyticsOut(BaseModel):
    period: DateRangeMetadata
    scope: AnalyticsScopeMetadata
    total_proposed_uses: int
    pending_reviews: int
    completed_reviews: int
    decisions_breakdown: dict[str, int]  # approve, decline, request_changes, needs_participant_discussion, escalate
    use_type_breakdown: dict[str, int]
    avg_turnaround_hours: float | None = None
    median_turnaround_hours: float | None = None


class OperationsAnalyticsOut(BaseModel):
    period: DateRangeMetadata
    scope: AnalyticsScopeMetadata
    total_tasks: int
    open_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    urgent_tasks: int
    high_priority_tasks: int
    overdue_tasks: int
    participant_follow_up_tasks: int
    unresolved_permission_tasks: int
    avg_resolution_hours: float | None = None


class WithdrawalAnalyticsOut(BaseModel):
    period: DateRangeMetadata
    scope: AnalyticsScopeMetadata
    total_withdrawal_requests: int
    active_withdrawals_in_period: int
    pending_care_tasks: int
    resolved_care_tasks: int
    avg_resolution_hours: float | None = None
    recent_withdrawal_events: list[dict[str, Any]] = Field(default_factory=list)


class AdvisoryAnalyticsOut(BaseModel):
    period: DateRangeMetadata
    scope: AnalyticsScopeMetadata
    total_advisory_runs: int
    runs_by_agent: dict[str, int]
    status_distribution: dict[str, int]
    alignment_rate: float | None = None
    alignment_sample_size: int = 0
    disclaimer: str = (
        "AI advisory outputs are strictly informational. Human decisions are authoritative. "
        "Concordance rates do not represent legal correctness or ethical validity."
    )


class TrendDataPoint(BaseModel):
    date: str  # YYYY-MM-DD
    consent_confirmed: int = 0
    reviews_decided: int = 0
    withdrawals_requested: int = 0
    tasks_completed: int = 0
    new_participants: int = 0


class TrendsAnalyticsOut(BaseModel):
    period: DateRangeMetadata
    scope: AnalyticsScopeMetadata
    interval: str
    series: list[TrendDataPoint]


class ExportRequestIn(BaseModel):
    project_id: uuid.UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    report_type: str = Field(
        default="overview",
        pattern="^(overview|consent_coverage|category_breakdown|reviews|operations|withdrawals)$",
    )
    format: str = Field(default="csv", pattern="^(csv|json)$")


class ExportResponseOut(BaseModel):
    report_type: str
    format: str
    filename: str
    generated_at: datetime
    content: str  # Base64 or raw string
