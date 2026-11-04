"""Participants and their protected contact records.

Contact details are stored Fernet-encrypted and are ONLY readable by
project_owner / producer / participant_care_lead (or the linked participant).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import CONTACT_TYPES, PARTICIPANT_STATUSES, in_clause
from app.models.base import Base, TimestampMixin, VersionMixin, uuid_pk


class Participant(Base, TimestampMixin, VersionMixin):
    __tablename__ = "participants"
    __table_args__ = (
        CheckConstraint(f"participant_status IN {in_clause(PARTICIPANT_STATUSES)}", name="ck_participants_status"),
        CheckConstraint("display_name <> ''", name="ck_participants_display_name_nonempty"),
        Index("ix_participants_project", "project_id"),
        Index("ix_participants_project_status", "project_id", "participant_status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    # Optional link to a user account with the 'participant' role (self-access).
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    preferred_language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_contact_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accessibility_requirements: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    privacy_preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    participant_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))


class ParticipantContactRecord(Base, TimestampMixin):
    __tablename__ = "participant_contact_records"
    __table_args__ = (
        CheckConstraint(f"contact_type IN {in_clause(CONTACT_TYPES)}", name="ck_contact_type"),
        Index("ix_contact_participant", "participant_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    contact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Fernet ciphertext; plaintext never touches the database, logs, or audit payloads.
    encrypted_contact_data: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
