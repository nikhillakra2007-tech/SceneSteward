"""Analytics export service — generates RFC 4180 compliant CSV and structured JSON reports."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.permissions import check_export_permission
from app.analytics.schemas import ExportRequestIn, ExportResponseOut
from app.analytics.service import (
    get_analytics_overview,
    get_consent_analytics,
    get_operations_analytics,
    get_review_analytics,
    get_withdrawal_analytics,
)
from app.models import User
from app.services import audit


def generate_analytics_export(
    db: Session,
    user: User,
    payload: ExportRequestIn,
) -> ExportResponseOut:
    """Validate authorization, generate analytical export, and record audit event."""
    # 1. Enforce export permission
    check_export_permission(db, user, payload.project_id)

    now = datetime.now(UTC)
    timestamp_slug = now.strftime("%Y%m%d_%H%M%S")
    report_type = payload.report_type
    fmt = payload.format.lower()
    project_id = payload.project_id

    content_str: str

    if report_type == "overview":
        overview = get_analytics_overview(
            db, user, project_id=project_id, start_date=payload.start_date, end_date=payload.end_date
        )
        if fmt == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["# SceneSteward Analytics Export: Executive Overview"])
            writer.writerow([f"# Generated At: {now.isoformat()}", f"User: {user.email}"])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Projects", overview.total_projects])
            writer.writerow(["Total Participants", overview.total_participants])
            writer.writerow(["Active Participants", overview.active_participants])
            writer.writerow(["Withdrawn Participants", overview.withdrawn_participants])
            writer.writerow(["Discussion Coverage (%)", f"{overview.discussion_coverage:.2f}%"])
            writer.writerow(["Approval Rate (%)", f"{overview.approval_rate:.2f}%"])
            writer.writerow(["Resolution Rate (%)", f"{overview.resolution_rate:.2f}%"])
            writer.writerow(["Unresolved Categories", overview.unresolved_categories])
            writer.writerow(["Pending Human Reviews", overview.pending_human_reviews])
            writer.writerow(["Completed Reviews", overview.completed_reviews])
            writer.writerow(["Withdrawal Requests", overview.withdrawal_requests])
            writer.writerow(["Urgent Care Tasks", overview.urgent_care_tasks])
            writer.writerow(["Open Care Tasks", overview.open_care_tasks])
            writer.writerow(["Overdue Tasks", overview.overdue_tasks])
            writer.writerow(["Avg Review Turnaround (Hours)", overview.avg_review_turnaround_hours or "N/A"])
            content_str = out.getvalue()
        else:
            content_str = overview.model_dump_json(indent=2)

    elif report_type in ("consent_coverage", "category_breakdown"):
        consent_out = get_consent_analytics(
            db, user, project_id=project_id, start_date=payload.start_date, end_date=payload.end_date
        )
        if fmt == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["# SceneSteward Analytics Export: Consent Category Breakdown"])
            writer.writerow([f"# Generated At: {now.isoformat()}", f"User: {user.email}"])
            writer.writerow([])
            writer.writerow([
                "Category",
                "Total Applicable",
                "Agreed",
                "Declined",
                "Needs Clarification",
                "Not Discussed",
                "Awaiting Confirmation",
                "Explained",
                "Discussion Coverage (%)",
                "Approval Rate (%)",
                "Resolution Rate (%)",
            ])
            for cat in consent_out.categories:
                writer.writerow([
                    cat.category,
                    cat.total_applicable,
                    cat.agreed,
                    cat.declined,
                    cat.needs_clarification,
                    cat.not_discussed,
                    cat.awaiting_confirmation,
                    cat.explained,
                    f"{cat.discussion_coverage:.2f}%",
                    f"{cat.approval_rate:.2f}%",
                    f"{cat.resolution_rate:.2f}%",
                ])
            content_str = out.getvalue()
        else:
            content_str = consent_out.model_dump_json(indent=2)

    elif report_type == "reviews":
        rev_out = get_review_analytics(
            db, user, project_id=project_id, start_date=payload.start_date, end_date=payload.end_date
        )
        if fmt == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["# SceneSteward Analytics Export: Proposed Use & Review Workflow"])
            writer.writerow([f"# Generated At: {now.isoformat()}", f"User: {user.email}"])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Proposed Uses", rev_out.total_proposed_uses])
            writer.writerow(["Pending Reviews", rev_out.pending_reviews])
            writer.writerow(["Completed Reviews", rev_out.completed_reviews])
            writer.writerow(["Avg Turnaround (Hours)", rev_out.avg_turnaround_hours or "N/A"])
            writer.writerow(["Median Turnaround (Hours)", rev_out.median_turnaround_hours or "N/A"])
            writer.writerow([])
            writer.writerow(["Human Decision", "Count"])
            for dec, count in rev_out.decisions_breakdown.items():
                writer.writerow([dec, count])
            writer.writerow([])
            writer.writerow(["Intended Use Type", "Count"])
            for ut, count in rev_out.use_type_breakdown.items():
                writer.writerow([ut, count])
            content_str = out.getvalue()
        else:
            content_str = rev_out.model_dump_json(indent=2)

    elif report_type == "operations":
        ops_out = get_operations_analytics(
            db, user, project_id=project_id, start_date=payload.start_date, end_date=payload.end_date
        )
        if fmt == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["# SceneSteward Analytics Export: Participant Care & Operations"])
            writer.writerow([f"# Generated At: {now.isoformat()}", f"User: {user.email}"])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Tasks", ops_out.total_tasks])
            writer.writerow(["Open Tasks", ops_out.open_tasks])
            writer.writerow(["In Progress Tasks", ops_out.in_progress_tasks])
            writer.writerow(["Completed Tasks", ops_out.completed_tasks])
            writer.writerow(["Urgent Tasks", ops_out.urgent_tasks])
            writer.writerow(["High Priority Tasks", ops_out.high_priority_tasks])
            writer.writerow(["Overdue Tasks", ops_out.overdue_tasks])
            writer.writerow(["Avg Task Resolution (Hours)", ops_out.avg_resolution_hours or "N/A"])
            content_str = out.getvalue()
        else:
            content_str = ops_out.model_dump_json(indent=2)

    elif report_type == "withdrawals":
        withdr_out = get_withdrawal_analytics(
            db, user, project_id=project_id, start_date=payload.start_date, end_date=payload.end_date
        )
        if fmt == "csv":
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["# SceneSteward Analytics Export: Withdrawal & Revocation Summary"])
            writer.writerow([f"# Generated At: {now.isoformat()}", f"User: {user.email}"])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Withdrawal Requests", withdr_out.total_withdrawal_requests])
            writer.writerow(["Pending Care Tasks", withdr_out.pending_care_tasks])
            writer.writerow(["Resolved Care Tasks", withdr_out.resolved_care_tasks])
            writer.writerow(["Avg Resolution (Hours)", withdr_out.avg_resolution_hours or "N/A"])
            writer.writerow([])
            writer.writerow(["Event Timestamp", "Event Action", "Participant ID", "Project ID"])
            for ev in withdr_out.recent_withdrawal_events:
                writer.writerow([
                    ev.get("timestamp"),
                    ev.get("action"),
                    ev.get("participant_id") or "Redacted",
                    ev.get("project_id"),
                ])
            content_str = out.getvalue()
        else:
            content_str = withdr_out.model_dump_json(indent=2)

    else:
        content_str = ""

    filename = f"scenesteward_analytics_{report_type}_{timestamp_slug}.{fmt}"

    # 2. Record immutable audit event for report generation
    if project_id:
        audit.record(
            db,
            project_id=project_id,
            participant_id=None,
            actor_type="user",
            actor_id=str(user.id),
            action="analytics.report_exported",
            entity_type="analytics_report",
            entity_id=None,
            new_value={"report_type": report_type, "format": fmt, "filename": filename},
        )
        db.commit()

    return ExportResponseOut(
        report_type=report_type,
        format=fmt,
        filename=filename,
        generated_at=now,
        content=content_str,
    )
