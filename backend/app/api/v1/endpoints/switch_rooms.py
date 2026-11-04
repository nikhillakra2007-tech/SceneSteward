"""Switch room linking (owner/producer) — create or reuse project/participant rooms."""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentUser, DbSession, get_membership, get_project_participant
from app.core import permissions
from app.core.exceptions import NotFoundError, PermissionDenied
from app.integrations.switch import get_switch_adapter, switch_status
from app.models import SwitchRoomLink
from app.schemas.common import ORMModel
from app.services import audit

router = APIRouter(prefix="/integrations/switch", tags=["switch"])

LINK_ROLES = {permissions.PROJECT_OWNER, permissions.PRODUCER}


class RoomLinkRequest(BaseModel):
    scope: str = Field(pattern="^(project|participant)$")
    participant_id: uuid.UUID | None = None
    connection_id: str | None = Field(default=None, description="Open agent connection id (required for real room creation)")


class RoomLinkOut(ORMModel):
    switch_room_id: str
    room_type: str
    reused: bool


@router.post("/projects/{project_id}/rooms", response_model=RoomLinkOut)
def link_room(project_id: uuid.UUID, payload: RoomLinkRequest,
              db: DbSession, user: CurrentUser) -> RoomLinkOut:
    membership = get_membership(db, project_id, user)
    if membership.role not in LINK_ROLES:
        raise PermissionDenied("Only owner or producer can link Switch rooms")

    participant = None
    if payload.scope == "participant":
        if payload.participant_id is None:
            raise NotFoundError("participant_id is required for participant scope")
        participant = get_project_participant(db, project_id, payload.participant_id)

    room_type = "project" if payload.scope == "project" else "participant_review"
    room_name = f"scenesteward-{room_type}-{project_id.hex[:8]}" + (f"-{participant.id.hex[:8]}" if participant else "")

    existing = (
        db.query(SwitchRoomLink)
        .filter(SwitchRoomLink.project_id == project_id,
                SwitchRoomLink.participant_id == (participant.id if participant else None),
                SwitchRoomLink.room_type == room_type)
        .first()
    )
    if existing:
        return RoomLinkOut(switch_room_id=existing.switch_room_id,
                           room_type=existing.room_type, reused=True)

    status = switch_status()
    if status.status != "configured_verified":
        from app.core.exceptions import UpstreamUnavailable
        raise UpstreamUnavailable(
            f"Switch is not verified ({status.status}); room not created",
            code="switch_not_verified",
        )
    adapter = get_switch_adapter()
    created = adapter.get_or_create_room(
        project_id=str(project_id),
        participant_id=str(participant.id) if participant else None,
        room_type=room_type, room_name=room_name, connection_id=payload.connection_id,
    )
    room = SwitchRoomLink(
        project_id=project_id,
        participant_id=participant.id if participant else None,
        room_type=room_type,
        switch_room_id=str(created["room_id"]),
        switch_room_name=room_name,
    )
    db.add(room)
    db.flush()
    audit.record(db, project_id=project_id,
                 participant_id=participant.id if participant else None,
                 actor_type="user", actor_id=str(user.id),
                 action="switch.room_linked", entity_type="switch_room_link", entity_id=room.id,
                 new_value={"room_type": room_type, "switch_room_id": room.switch_room_id})
    db.commit()
    return RoomLinkOut(switch_room_id=room.switch_room_id, room_type=room_type, reused=False)
