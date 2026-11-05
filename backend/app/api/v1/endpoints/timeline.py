"""Accountability timelines — keyset-paginated, role-filtered audit feeds."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, DbSession, OptionalUser, get_membership
from app.core import permissions
from app.core.database import system_context
from app.core.exceptions import NotFoundError, PermissionDenied, Unauthenticated
from app.core.security import decode_participant_token
from app.models import Participant
from app.schemas.timeline import TimelineEntry
from app.services.timeline import DEFAULT_LIMIT, MAX_LIMIT, timeline_query

router = APIRouter(tags=["timeline"])


def _entries(rows, next_cursor) -> dict:
    return {
        "items": [
            TimelineEntry(
                id=e.id, timestamp=e.timestamp, actor_type=e.actor_type,
                action=e.action, entity_type=e.entity_type, entity_id=e.entity_id,
                reason=e.reason, correlation_id=e.correlation_id,
                participant_id=e.participant_id,
            ).model_dump(mode="json")
            for e in rows
        ],
        "next_cursor": next_cursor,
    }


@router.get("/projects/{project_id}/timeline")
def project_timeline(project_id: uuid.UUID, db: DbSession, user: CurrentUser,
                     limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
                     cursor: str | None = Query(default=None)) -> dict:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view the timeline")
    rows, next_cursor = timeline_query(db, project_id=project_id, participant_id=None,
                                       viewer_role=membership.role, limit=limit, cursor=cursor)
    return _entries(rows, next_cursor)


@router.get("/participants/{participant_id}/timeline")
def participant_timeline(
    participant_id: uuid.UUID,
    db: DbSession,
    user: OptionalUser,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None),
    token: str | None = None,
) -> dict:
    if token:
        claims = decode_participant_token(token)
        if claims.get("sub") != str(participant_id):
            raise PermissionDenied("Access token does not match this participant")
        with system_context(db):
            participant = db.get(Participant, participant_id)
            if participant is None or str(participant.project_id) != claims.get("project_id"):
                raise NotFoundError("Participant not found")
            rows, next_cursor = timeline_query(
                db,
                project_id=participant.project_id,
                participant_id=participant.id,
                viewer_role=permissions.PARTICIPANT,
                limit=limit,
                cursor=cursor,
            )
            return _entries(rows, next_cursor)

    if user is None:
        raise Unauthenticated("Authentication or participant token required")

    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    is_self = participant.user_id == user.id
    if not is_self and membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view the timeline")
    if membership.role == permissions.PARTICIPANT and not is_self:
        raise NotFoundError("Participant not found")
    rows, next_cursor = timeline_query(db, project_id=participant.project_id,
                                       participant_id=participant.id,
                                       viewer_role=membership.role, limit=limit, cursor=cursor)
    return _entries(rows, next_cursor)
