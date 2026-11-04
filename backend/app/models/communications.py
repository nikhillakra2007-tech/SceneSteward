"""Participant communications. A draft is never a sent communication:
sending requires approved_by + approved status first (also CHECK-enforced)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import COMMUNICATION_STATUSES, COMMUNICATION_TYPES, in_clause
from app.models.base import Base, CreatedAtMixin, uuid_pk


class ParticipantCommunication(Base, CreatedAtMixin):
    __tablename__ = "participant_communications"
    __table_args__ = (
        CheckConstraint(f"communication_type IN {in_clause(COMMUNICATION_TYPES)}", name="ck_comms_type"),
        CheckConstraint(f"communication_status IN {in_clause(COMMUNICATION_STATUSES)}", name="ck_comms_status"),
        CheckConstraint(
            "communication_status <> 'sent' OR (approved_by IS NOT NULL AND sent_at IS NOT NULL)",
            name="ck_comms_sent_requires_approval",
        ),
        Index("ix_comms_project_participant", "project_id", "participant_id"),
        Index("ix_comms_status", "communication_status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    communication_type: Mapped[str] = mapped_column(String(24), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(300), nullable=True)
    draft_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    communication_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'draft'"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
