"""Story elements — readable by members; identifying details restricted."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession, get_membership
from app.core import permissions
from app.core.exceptions import ConflictError, NotFoundError, PermissionDenied
from app.models import StoryElement
from app.schemas.common import Page
from app.schemas.story import StoryElementCreate, StoryElementOut, StoryElementUpdate
from app.services import audit
from app.utils.pagination import PageParams, page_params

router = APIRouter(tags=["story"])

IDENTIFYING_ROLES = {permissions.PROJECT_OWNER, permissions.PRODUCER,
                     permissions.DIRECTOR, permissions.PARTICIPANT_CARE_LEAD}


def _out(e: StoryElement, role: str) -> StoryElementOut:
    out = StoryElementOut.model_validate(e)
    if role not in IDENTIFYING_ROLES:
        out.identifying_details = []  # hidden, not even hinted at
    return out


@router.post("/projects/{project_id}/story-elements", response_model=StoryElementOut, status_code=201)
def create_story_element(project_id: uuid.UUID, payload: StoryElementCreate,
                         db: DbSession, user: CurrentUser) -> StoryElementOut:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.STORY_WRITE_ROLES:
        raise PermissionDenied("This role cannot create story elements")
    element = StoryElement(
        project_id=project_id, title=payload.title.strip(),
        scene_reference=payload.scene_reference, description=payload.description,
        identifying_details=payload.identifying_details,
        sensitivity_level=payload.sensitivity_level, created_by=user.id,
    )
    db.add(element)
    db.flush()
    audit.record(db, project_id=project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="story_element.created", entity_type="story_element", entity_id=element.id,
                 new_value={"title": element.title, "sensitivity_level": element.sensitivity_level})
    db.commit()
    db.refresh(element)
    return _out(element, membership.role)


@router.get("/projects/{project_id}/story-elements", response_model=Page[StoryElementOut])
def list_story_elements(project_id: uuid.UUID, db: DbSession, user: CurrentUser,
                        page: Annotated[PageParams, Depends(page_params)]) -> Page[StoryElementOut]:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view story elements")
    stmt = select(StoryElement).where(StoryElement.project_id == project_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(StoryElement.created_at.asc())
                      .limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[_out(e, membership.role) for e in rows],
                total=total, limit=page.limit, offset=page.offset)


def _get_scoped(db, element_id: uuid.UUID, project_id: uuid.UUID | None, user: CurrentUser):
    element = db.get(StoryElement, element_id)
    if element is None:
        raise NotFoundError("Story element not found")
    membership = get_membership(db, element.project_id, user)
    if project_id is not None and element.project_id != project_id:
        raise NotFoundError("Story element not found")
    return element, membership


@router.get("/story-elements/{story_element_id}", response_model=StoryElementOut)
def get_story_element(story_element_id: uuid.UUID, db: DbSession, user: CurrentUser) -> StoryElementOut:
    element, membership = _get_scoped(db, story_element_id, None, user)
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view story elements")
    return _out(element, membership.role)


@router.patch("/story-elements/{story_element_id}", response_model=StoryElementOut)
def update_story_element(story_element_id: uuid.UUID, payload: StoryElementUpdate,
                         db: DbSession, user: CurrentUser) -> StoryElementOut:
    element, membership = _get_scoped(db, story_element_id, None, user)
    if membership.role not in permissions.STORY_WRITE_ROLES:
        raise PermissionDenied("This role cannot edit story elements")
    if element.version != payload.expected_version:
        raise ConflictError("Story element was modified by another writer; reload and retry",
                            code="version_conflict")
    previous = {"title": element.title, "sensitivity_level": element.sensitivity_level}
    for field in ("title", "scene_reference", "description", "identifying_details", "sensitivity_level"):
        value = getattr(payload, field)
        if value is not None:
            setattr(element, field, value)
    element.version += 1
    element.updated_at = datetime.now(UTC)
    audit.record(db, project_id=element.project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="story_element.updated", entity_type="story_element", entity_id=element.id,
                 previous_value=previous,
                 new_value={"title": element.title, "sensitivity_level": element.sensitivity_level})
    db.commit()
    db.refresh(element)
    return _out(element, membership.role)
