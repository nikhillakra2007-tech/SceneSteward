"""Participant communication endpoints.

Guarantees:
- Silence is never agreement.
- AI agents / workflows can draft communications, but they can NEVER be sent without human approval.
- Database CHECK constraint enforces approved_by IS NOT NULL before status='sent'.
- Sending without configured provider fails closed (503) without mutating status to sent.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession, get_membership
from app.core import permissions
from app.core.exceptions import NotFoundError, PermissionDenied, PreconditionFailed, UpstreamUnavailable
from app.models.communications import ParticipantCommunication
from app.models.participants import Participant
from app.schemas.communications import (
    CommunicationApprove,
    CommunicationCreate,
    CommunicationOut,
)
from app.services import audit

router = APIRouter(tags=["communications"])


@router.get("/projects/{project_id}/communications", response_model=list[CommunicationOut])
def list_project_communications(
    project_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    participant_id: uuid.UUID | None = None,
) -> list[CommunicationOut]:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.SENSITIVE_READ_ROLES:
        raise PermissionDenied("You do not have permission to view participant communications")

    query = select(ParticipantCommunication).where(ParticipantCommunication.project_id == project_id)
    if participant_id:
        query = query.where(ParticipantCommunication.participant_id == participant_id)
    query = query.order_by(ParticipantCommunication.created_at.desc())

    comms = db.execute(query).scalars().all()
    return [CommunicationOut.model_validate(c) for c in comms]


@router.post("/projects/{project_id}/communications", response_model=CommunicationOut, status_code=201)
def create_draft_communication(
    project_id: uuid.UUID,
    payload: CommunicationCreate,
    db: DbSession,
    user: CurrentUser,
) -> CommunicationOut:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.PARTICIPANT_WRITE_ROLES:
        raise PermissionDenied("This role cannot draft participant communications")

    part = db.get(Participant, payload.participant_id)
    if part is None or part.project_id != project_id:
        raise NotFoundError("Participant not found in this project")

    comm = ParticipantCommunication(
        project_id=project_id,
        participant_id=payload.participant_id,
        communication_type=payload.communication_type,
        subject=payload.subject,
        draft_content=payload.draft_content,
        communication_status="draft",
        created_by=user.id,
    )
    db.add(comm)
    db.flush()
    audit.record(
        db,
        project_id=project_id,
        participant_id=payload.participant_id,
        actor_type="user",
        actor_id=str(user.id),
        action="communication.draft_created",
        entity_type="participant_communication",
        entity_id=comm.id,
        new_value={"communication_type": comm.communication_type, "subject": comm.subject},
    )
    db.commit()
    db.refresh(comm)
    return CommunicationOut.model_validate(comm)


@router.post("/communications/{communication_id}/approve", response_model=CommunicationOut)
def approve_communication(
    communication_id: uuid.UUID,
    payload: CommunicationApprove,
    db: DbSession,
    user: CurrentUser,
) -> CommunicationOut:
    comm = db.get(ParticipantCommunication, communication_id)
    if comm is None:
        raise NotFoundError("Communication not found")

    membership = get_membership(db, comm.project_id, user)
    # Only owner, producer, or participant_care_lead can approve
    if membership.role not in permissions.CONSENT_CONFIRM_ROLES:
        raise PermissionDenied("Only project owners, producers, or participant care leads can approve communications")

    if comm.communication_status == "approved":
        return CommunicationOut.model_validate(comm)
    if comm.communication_status != "draft":
        raise PreconditionFailed(f"Cannot approve communication in status {comm.communication_status}")

    comm.communication_status = "approved"
    comm.approved_by = user.id

    audit.record(
        db,
        project_id=comm.project_id,
        participant_id=comm.participant_id,
        actor_type="user",
        actor_id=str(user.id),
        action="communication.approved",
        entity_type="participant_communication",
        entity_id=comm.id,
        new_value={"approved_by": str(user.id), "notes": payload.notes},
    )
    db.commit()
    db.refresh(comm)
    return CommunicationOut.model_validate(comm)


@router.post("/communications/{communication_id}/send", response_model=CommunicationOut)
def send_communication(
    communication_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> CommunicationOut:
    comm = db.get(ParticipantCommunication, communication_id)
    if comm is None:
        raise NotFoundError("Communication not found")

    membership = get_membership(db, comm.project_id, user)
    if membership.role not in permissions.CONSENT_CONFIRM_ROLES:
        raise PermissionDenied("Only project owners, producers, or care leads can trigger communication delivery")

    # MUST be approved first
    if comm.communication_status != "approved":
        raise PreconditionFailed(
            f"Communication status is {comm.communication_status!r}; human approval is required before delivery",
            code="approval_required",
        )

    # Check for live outbound dispatch provider
    audit.record(
        db,
        project_id=comm.project_id,
        participant_id=comm.participant_id,
        actor_type="user",
        actor_id=str(user.id),
        action="communication.send_attempted",
        entity_type="participant_communication",
        entity_id=comm.id,
        new_value={"result": "no_provider_configured"},
    )
    db.commit()

    # Fail closed: never falsely claim sent
    raise UpstreamUnavailable(
        "No outbound participant communication provider is configured; communications cannot be dispatched automatically. Use external verified channels or copy the approved draft.",
        code="no_provider_configured",
    )
