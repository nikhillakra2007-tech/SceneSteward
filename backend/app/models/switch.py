"""Links between SceneSteward projects/participants and Switch rooms.

Least privilege: participant_review rooms are 1:1 with a participant and must
never carry another participant's information.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import SWITCH_ROOM_TYPES, in_clause
from app.models.base import Base, CreatedAtMixin, uuid_pk


class SwitchRoomLink(Base, CreatedAtMixin):
    __tablename__ = "switch_room_links"
    __table_args__ = (
        UniqueConstraint("switch_room_id", name="uq_switch_room_links_room"),
        UniqueConstraint("project_id", "participant_id", "room_type", name="uq_switch_room_links_scope"),
        CheckConstraint(f"room_type IN {in_clause(SWITCH_ROOM_TYPES)}", name="ck_switch_room_type"),
        Index("ix_switch_room_links_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    # NULL for project-wide rooms; set for participant-specific review rooms.
    participant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=True)
    room_type: Mapped[str] = mapped_column(String(24), nullable=False)
    switch_room_id: Mapped[str] = mapped_column(String(255), nullable=False)
    switch_room_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
