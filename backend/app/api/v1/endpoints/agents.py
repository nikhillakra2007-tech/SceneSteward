"""Agent runs — manual trigger (restricted), read, findings listing."""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.agents import agent_for
from app.api.dependencies import CurrentUser, DbSession, get_membership
from app.core import permissions
from app.core.exceptions import NotFoundError, PermissionDenied
from app.models import AgentRun, Participant, ProposedUse, StoryElement
from app.schemas.agents import AgentRequest, AgentRunDetailOut
from app.services import consent_service
from app.services.agent_context import build_context

router = APIRouter(prefix="/agents", tags=["agents"])

RUN_ROLES = {permissions.PROJECT_OWNER, permissions.PRODUCER, permissions.PARTICIPANT_CARE_LEAD}


@router.post("/runs", response_model=AgentRunDetailOut, status_code=201)
def trigger_agent_run(payload: AgentRequest, db: DbSession, user: CurrentUser) -> AgentRunDetailOut:
    use = db.get(ProposedUse, payload.proposed_use_id)
    if use is None:
        raise NotFoundError("Proposed use not found")
    membership = get_membership(db, use.project_id, user)
    if membership.role not in RUN_ROLES:
        raise PermissionDenied("This role cannot trigger agent runs")

    participant = db.get(Participant, use.participant_id)
    story_element = db.get(StoryElement, use.story_element_id) if use.story_element_id else None
    latest = consent_service.get_latest_confirmed(db, participant.id) if participant else None
    history = consent_service.get_confirmed_history(db, participant.id) if participant else []
    from app.models import ProposedUseAnalysis
    analysis = db.execute(
        select(ProposedUseAnalysis).where(ProposedUseAnalysis.proposed_use_id == use.id)
        .order_by(ProposedUseAnalysis.created_at.desc()).limit(1)
    ).scalar_one_or_none()

    context = build_context(
        agent_name=payload.agent_name,
        project_id=use.project_id,
        participant_id=participant.id if participant else None,
        proposed_use=use,
        story_element=story_element,
        latest_confirmed=latest,
        confirmed_history=history,
        analysis_findings=analysis.findings if analysis else [],
        analysis_outcome=analysis.outcome if analysis else None,
        participant_private={
            "accessibility_requirements": participant.accessibility_requirements,
            "preferred_language": participant.preferred_language,
            "privacy_preferences": participant.privacy_preferences,
        } if participant else {},
    )
    import uuid as _uuid
    corr = _uuid.uuid4()
    run = agent_for(payload.agent_name).execute(db, context=context, actor=("agent", payload.agent_name),
                                                correlation_id=corr)
    db.commit()
    db.refresh(run)
    out = AgentRunDetailOut.model_validate(run)
    return out


@router.get("/runs/{run_id}", response_model=AgentRunDetailOut)
def get_run(run_id: uuid.UUID, db: DbSession, user: CurrentUser) -> AgentRunDetailOut:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise NotFoundError("Agent run not found")
    membership = get_membership(db, run.project_id, user)
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view agent runs")
    return AgentRunDetailOut.model_validate(run)
