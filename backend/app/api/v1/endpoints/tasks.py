"""Human-owned tasks: list + update (status/owner/due/priority)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession, get_membership
from app.core import permissions
from app.core.exceptions import NotFoundError, PermissionDenied
from app.models import Task
from app.schemas.common import Page
from app.schemas.timeline import TaskOut, TaskUpdate
from app.services import audit
from app.utils.pagination import PageParams, page_params

router = APIRouter(tags=["tasks"])


def _out(t: Task) -> TaskOut:
    return TaskOut.model_validate(t)


@router.get("/projects/{project_id}/tasks", response_model=Page[TaskOut])
def list_tasks(project_id: uuid.UUID, db: DbSession, user: CurrentUser,
               page: Annotated[PageParams, Depends(page_params)],
               status: str | None = None, owner_user_id: uuid.UUID | None = None) -> Page[TaskOut]:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view tasks")
    stmt = select(Task).where(Task.project_id == project_id)
    if status:
        stmt = stmt.where(Task.status == status)
    if owner_user_id:
        stmt = stmt.where(Task.owner_user_id == owner_user_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Task.created_at.desc())
                      .limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[_out(t) for t in rows], total=total, limit=page.limit, offset=page.offset)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: uuid.UUID, payload: TaskUpdate, db: DbSession, user: CurrentUser) -> TaskOut:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError("Task not found")
    membership = get_membership(db, task.project_id, user)
    manage = membership.role in permissions.TASK_WRITE_ROLES
    is_owner = task.owner_user_id == user.id
    if not (manage or is_owner):
        raise PermissionDenied("Only the assignee or project staff can update this task")
    previous = {"status": task.status, "owner_user_id": str(task.owner_user_id) if task.owner_user_id else None}
    data = payload.model_dump(exclude_unset=True)
    # An assignee may only advance their own task's status, not reassign it.
    if not manage:
        data = {k: v for k, v in data.items() if k in ("status",)}
    for field, value in data.items():
        setattr(task, field, value)
    if payload.status == "done" and task.completed_at is None:
        task.completed_at = datetime.now(UTC)
    task.updated_at = datetime.now(UTC)
    audit.record(db, project_id=task.project_id, participant_id=task.participant_id,
                 actor_type="user", actor_id=str(user.id),
                 action="task.updated", entity_type="task", entity_id=task.id,
                 previous_value=previous,
                 new_value={"status": task.status,
                            "owner_user_id": str(task.owner_user_id) if task.owner_user_id else None})
    db.commit()
    db.refresh(task)
    return _out(task)
