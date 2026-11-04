"""Participant communications — drafts never become sends without human approval.

No email/SMS provider is wired in the MVP; 'mark sent' records the state
transition after a human has approved and (externally) delivered the message.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import PreconditionFailed
from app.models import ParticipantCommunication
from app.services import audit


def approve(db: Session, *, comm: ParticipantCommunication, actor_user_id: uuid.UUID,
            actor: tuple[str, str], correlation_id: uuid.UUID) -> ParticipantCommunication:
    if comm.communication_status not in ("draft", "awaiting_approval"):
        raise PreconditionFailed("Only drafts can be approved", code="invalid_state")
    comm.communication_status = "approved"
    comm.approved_by = actor_user_id
    audit.record(db, project_id=comm.project_id, participant_id=comm.participant_id,
                 actor_type=actor[0], actor_id=actor[1],
                 action="communication.approved", entity_type="participant_communication",
                 entity_id=comm.id, correlation_id=correlation_id)
    return comm


def mark_sent(db: Session, *, comm: ParticipantCommunication, actor_user_id: uuid.UUID,
              actor: tuple[str, str], correlation_id: uuid.UUID) -> ParticipantCommunication:
    if comm.communication_status != "approved" or comm.approved_by is None:
        raise PreconditionFailed("Communication must be approved by a human before it can be sent",
                                 code="not_approved")
    comm.communication_status = "sent"
    comm.sent_at = datetime.now(UTC)
    audit.record(db, project_id=comm.project_id, participant_id=comm.participant_id,
                 actor_type=actor[0], actor_id=actor[1],
                 action="communication.sent", entity_type="participant_communication",
                 entity_id=comm.id, correlation_id=correlation_id)
    return comm
