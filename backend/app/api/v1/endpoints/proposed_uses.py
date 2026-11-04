"""Proposed uses — create, analyse (workflow), read, limited update."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession, get_membership
from app.core import permissions
from app.core.exceptions import ConflictError, NotFoundError, PermissionDenied
from app.models import Participant, ProposedUse, ProposedUseAnalysis, StoryElement
from app.schemas.common import Page
from app.schemas.uses import (
    AnalyseResponse,
    AnalysisOut,
    ProposedUseCreate,
    ProposedUseOut,
    ProposedUseUpdate,
)
from app.services import audit
from app.utils.pagination import PageParams, page_params
from app.workflows.proposed_use_analysis import run_proposed_use_analysis

router = APIRouter(tags=["proposed-uses"])


def _out(p: ProposedUse) -> ProposedUseOut:
    return ProposedUseOut.model_validate(p)


def _load_participant_in_project(db, project_id: uuid.UUID, participant_id: uuid.UUID) -> Participant:
    participant = db.get(Participant, participant_id)
    if participant is None or participant.project_id != project_id:
        raise NotFoundError("Participant not found")
    return participant


@router.post("/projects/{project_id}/proposed-uses", response_model=ProposedUseOut, status_code=201)
def create_proposed_use(project_id: uuid.UUID, payload: ProposedUseCreate,
                        db: DbSession, user: CurrentUser) -> ProposedUseOut:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.STORY_WRITE_ROLES:
        raise PermissionDenied("This role cannot propose uses")
    participant = _load_participant_in_project(db, project_id, payload.participant_id)
    if payload.story_element_id is not None:
        element = db.get(StoryElement, payload.story_element_id)
        if element is None or element.project_id != project_id:
            raise NotFoundError("Story element not found")
    use = ProposedUse(
        project_id=project_id, participant_id=participant.id,
        story_element_id=payload.story_element_id,
        use_type=payload.use_type.strip(), platform=payload.platform,
        audience=payload.audience, purpose=payload.purpose, territory=payload.territory,
        context_description=payload.context_description,
        status="submitted", proposed_by=user.id,
    )
    db.add(use)
    db.flush()
    audit.record(db, project_id=project_id, participant_id=participant.id,
                 actor_type="user", actor_id=str(user.id),
                 action="proposed_use.created", entity_type="proposed_use", entity_id=use.id,
                 new_value={"use_type": use.use_type, "platform": use.platform})
    db.commit()
    db.refresh(use)
    if payload.run_analysis:
        run_proposed_use_analysis(db, proposed_use=use, project_id=project_id,
                                  actor_user_id=user.id, correlation_id=uuid.uuid4())
        db.commit()
        db.refresh(use)
    return _out(use)


@router.get("/projects/{project_id}/proposed-uses", response_model=Page[ProposedUseOut])
def list_proposed_uses(project_id: uuid.UUID, db: DbSession, user: CurrentUser,
                       page: Annotated[PageParams, Depends(page_params)],
                       status: str | None = None) -> Page[ProposedUseOut]:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view proposed uses")
    stmt = select(ProposedUse).where(ProposedUse.project_id == project_id)
    if status:
        stmt = stmt.where(ProposedUse.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(ProposedUse.created_at.desc())
                      .limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[_out(p) for p in rows], total=total, limit=page.limit, offset=page.offset)


def _get_scoped(db, proposed_use_id: uuid.UUID, user: CurrentUser, roles: set[str] | None, action: str):
    use = db.get(ProposedUse, proposed_use_id)
    if use is None:
        raise NotFoundError("Proposed use not found")
    membership = get_membership(db, use.project_id, user)
    if roles is not None and membership.role not in roles:
        raise PermissionDenied(f"This role cannot perform that operation ({action})")
    return use, membership


@router.get("/proposed-uses/{proposed_use_id}", response_model=ProposedUseOut)
def get_proposed_use(proposed_use_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ProposedUseOut:
    use, membership = _get_scoped(db, proposed_use_id, user, None, "view")
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view proposed uses")
    return _out(use)


@router.patch("/proposed-uses/{proposed_use_id}", response_model=ProposedUseOut)
def update_proposed_use(proposed_use_id: uuid.UUID, payload: ProposedUseUpdate,
                        db: DbSession, user: CurrentUser) -> ProposedUseOut:
    use, _membership = _get_scoped(db, proposed_use_id, user, permissions.STORY_WRITE_ROLES, "edit")
    if use.version != payload.expected_version:
        raise ConflictError("Proposed use was modified by another writer; reload and retry",
                            code="version_conflict")
    # Status is only changed by the workflow/decision endpoints, except withdrawal.
    if payload.status is not None and payload.status != "withdrawn":
        raise PermissionDenied("status may only be set to 'withdrawn' here; other transitions happen via analyse/decision endpoints")
    previous = {"use_type": use.use_type, "status": use.status}
    for field in ("use_type", "platform", "audience", "purpose", "territory", "context_description", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(use, field, value)
    use.version += 1
    use.updated_at = datetime.now(UTC)
    audit.record(db, project_id=use.project_id, participant_id=use.participant_id,
                 actor_type="user", actor_id=str(user.id),
                 action="proposed_use.updated", entity_type="proposed_use", entity_id=use.id,
                 previous_value=previous, new_value={"use_type": use.use_type, "status": use.status})
    db.commit()
    db.refresh(use)
    return _out(use)


@router.post("/proposed-uses/{proposed_use_id}/analyse", response_model=AnalyseResponse)
def analyse_proposed_use(proposed_use_id: uuid.UUID, db: DbSession, user: CurrentUser) -> AnalyseResponse:
    use, _membership = _get_scoped(db, proposed_use_id, user, permissions.STORY_WRITE_ROLES, "analyse")
    outcome = run_proposed_use_analysis(db, proposed_use=use, project_id=use.project_id,
                                        actor_user_id=user.id, correlation_id=uuid.uuid4())
    db.commit()
    analysis = db.get(ProposedUseAnalysis, outcome["analysis_id"])
    return AnalyseResponse(
        proposed_use_id=use.id,
        analysis=AnalysisOut.model_validate(analysis),
        outcome=outcome["outcome"],
        requires_human_review=True,
        tasks_created=outcome["task_ids"],
        review_id=outcome["review_id"],
    )


@router.get("/proposed-uses/{proposed_use_id}/agent-findings", response_model=list[dict])
def agent_findings(proposed_use_id: uuid.UUID, db: DbSession, user: CurrentUser) -> list[dict]:
    use, membership = _get_scoped(db, proposed_use_id, user, None, "view")
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view agent findings")
    from app.models import AgentRun
    rows = db.execute(
        select(AgentRun).where(AgentRun.proposed_use_id == use.id)
        .order_by(AgentRun.created_at.asc())
    ).scalars().all()
    return [
        {"agent_name": r.agent_name, "run_id": str(r.id), "execution_status": r.execution_status,
         "error_code": r.error_code, "output_data": r.output_data,
         "model_provider": r.model_provider, "model_version": r.model_version,
         "created_at": r.created_at.isoformat()}
        for r in rows
    ]
