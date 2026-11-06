"""Authorization rules and permission gates for SceneSteward Analytics."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDenied
from app.core.permissions import (
    DIRECTOR,
    EDITOR,
    PARTICIPANT_CARE_LEAD,
    PRODUCER,
    PROJECT_OWNER,
    VIEWER,
)
from app.models import ProjectMembership, User

ANALYTICS_READ_ROLES = {
    PROJECT_OWNER,
    PRODUCER,
    DIRECTOR,
    EDITOR,
    PARTICIPANT_CARE_LEAD,
    VIEWER,
}

ANALYTICS_EXPORT_ROLES = {
    PROJECT_OWNER,
    PRODUCER,
    DIRECTOR,
    PARTICIPANT_CARE_LEAD,
}


def get_authorized_project_ids(
    db: Session,
    user: User,
    requested_project_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    """Retrieve list of project IDs that the user is authorized to analyze.

    If requested_project_id is provided:
      Validates user's active membership and role in that specific project.
      Raises NotFoundError (no existence oracle) if not a member.
      Raises PermissionDenied if the user's role is not authorized (e.g., 'participant').
    If requested_project_id is None:
      Returns all project IDs where user has an authorized role with active membership.
    """
    if requested_project_id is not None:
        stmt = select(ProjectMembership).where(
            ProjectMembership.project_id == requested_project_id,
            ProjectMembership.user_id == user.id,
            ProjectMembership.membership_status == "active",
        )
        membership = db.execute(stmt).scalar_one_or_none()
        if membership is None:
            # Consistent with SceneSteward security model: do not disclose project existence
            raise NotFoundError("Project not found")

        if membership.role not in ANALYTICS_READ_ROLES:
            raise PermissionDenied("Your role cannot view analytics for this project")

        return [requested_project_id]

    # Portfolio-level scope across all authorized projects for this user
    stmt = select(ProjectMembership.project_id).where(
        ProjectMembership.user_id == user.id,
        ProjectMembership.membership_status == "active",
        ProjectMembership.role.in_(ANALYTICS_READ_ROLES),
    )
    project_ids = list(db.execute(stmt).scalars().all())
    return project_ids


def check_export_permission(
    db: Session,
    user: User,
    project_id: uuid.UUID | None = None,
) -> None:
    """Validate that user has permission to generate/download analytical reports."""
    if project_id is not None:
        stmt = select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user.id,
            ProjectMembership.membership_status == "active",
        )
        membership = db.execute(stmt).scalar_one_or_none()
        if membership is None:
            raise NotFoundError("Project not found")
        if membership.role not in ANALYTICS_EXPORT_ROLES:
            raise PermissionDenied("Your role cannot export analytics reports")
    else:
        # Cross-project export requires at least one project with export rights
        stmt = select(ProjectMembership).where(
            ProjectMembership.user_id == user.id,
            ProjectMembership.membership_status == "active",
            ProjectMembership.role.in_(ANALYTICS_EXPORT_ROLES),
        )
        if not db.execute(stmt).scalars().first():
            raise PermissionDenied("You do not hold export authorization on any projects")
