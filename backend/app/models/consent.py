"""Consent records (versioned) and consent choices.

A consent record is an immutable snapshot once participant_confirmation='confirmed'.
New facts create a new version; older confirmed versions are marked 'superseded'.
Silence is never agreement: categories absent from the latest confirmed record
are 'not_discussed' for comparison purposes.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.choices import (
    CONSENT_CHOICES,
    CONSENT_RECORD_STATUSES,
    PARTICIPANT_CONFIRMATIONS,
    SOURCE_TYPES,
    in_clause,
)
from app.models.base import Base, CreatedAtMixin, VersionMixin, uuid_pk


class ConsentRecord(Base, CreatedAtMixin, VersionMixin):
    __tablename__ = "consent_records"
    __table_args__ = (
        UniqueConstraint("participant_id", "version_number", name="uq_consent_records_participant_version"),
        CheckConstraint(f"record_status IN {in_clause(CONSENT_RECORD_STATUSES)}", name="ck_consent_record_status"),
        CheckConstraint(f"participant_confirmation IN {in_clause(PARTICIPANT_CONFIRMATIONS)}", name="ck_consent_confirmation"),
        CheckConstraint(f"source_type IN {in_clause(SOURCE_TYPES)}", name="ck_consent_source_type"),
        CheckConstraint("version_number >= 1", name="ck_consent_version_positive"),
        Index("ix_consent_records_participant", "participant_id"),
        Index("ix_consent_records_project", "project_id"),
        Index("ix_consent_records_participant_status", "participant_id", "record_status", "version_number"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    record_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'draft'"))
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("release_documents.id", ondelete="SET NULL"), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    participant_confirmation: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'unconfirmed'"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    choices: Mapped[list[ConsentChoice]] = relationship(
        back_populates="record", cascade="all, delete-orphan", lazy="selectin"
    )


class ConsentChoice(Base, CreatedAtMixin):
    __tablename__ = "consent_choices"
    __table_args__ = (
        CheckConstraint(f"choice IN {in_clause(CONSENT_CHOICES)}", name="ck_consent_choice_value"),
        CheckConstraint("category <> '' AND length(category) <= 100", name="ck_consent_choice_category"),
        CheckConstraint("confidence_if_extracted IS NULL OR (confidence_if_extracted >= 0 AND confidence_if_extracted <= 1)", name="ck_consent_choice_confidence"),
        Index("ix_consent_choices_record", "consent_record_id"),
        Index("ix_consent_choices_category", "category"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    consent_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consent_records.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    choice: Mapped[str] = mapped_column(String(32), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'manual'"))
    confidence_if_extracted: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    record: Mapped[ConsentRecord] = relationship(back_populates="choices")
