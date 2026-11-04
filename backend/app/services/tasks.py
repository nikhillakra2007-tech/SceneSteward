"""Task creation and assignment helpers."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.models import Task


def default_assignee_for_participant_work(db: Session, project_id: uuid.UUID) -> uuid.UUID | None:
    """Prefer an active participant_care_lead; fall back to producer, then owner."""
    for role in ("participant_care_lead", "producer", "project_owner"):
        stmt = select(models.ProjectMembership.user_id).where(
            models.ProjectMembership.project_id == project_id,
            models.ProjectMembership.role == role,
            models.ProjectMembership.membership_status == "active",
        ).order_by(models.ProjectMembership.created_at.asc()).limit(1)
        user_id = db.execute(stmt).scalar_one_or_none()
        if user_id:
            return user_id
    return None


def create_task(
    db: Session,
    *,
    project_id: uuid.UUID,
    participant_id: uuid.UUID | None,
    task_type: str,
    title: str,
    description: str | None = None,
    owner_user_id: uuid.UUID | None | str = "auto",
    priority: str = "normal",
    due_at: datetime | None = None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    created_by_actor_type: str = "system",
) -> Task:
    if owner_user_id == "auto":
        owner_user_id = default_assignee_for_participant_work(db, project_id)
    task = Task(
        project_id=project_id,
        participant_id=participant_id,
        task_type=task_type,
        title=title[:300],
        description=description,
        owner_user_id=owner_user_id,
        priority=priority,
        due_at=due_at,
        source_type=source_type,
        source_id=source_id,
        created_by_actor_type=created_by_actor_type,
    )
    db.add(task)
    db.flush()
    return task
