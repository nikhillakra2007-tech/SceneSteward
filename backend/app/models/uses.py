"""Proposed uses (what production wants to do with a story element) and the
persisted outputs of the comparison engine."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import ANALYSIS_OUTCOMES, PROPOSED_USE_STATUSES, in_clause
from app.models.base import Base, CreatedAtMixin, TimestampMixin, VersionMixin, uuid_pk


class ProposedUse(Base, TimestampMixin, VersionMixin):
    __tablename__ = "proposed_uses"
    __table_args__ = (
        CheckConstraint(f"status IN {in_clause(PROPOSED_USE_STATUSES)}", name="ck_uses_status"),
        CheckConstraint("use_type <> ''", name="ck_uses_use_type_nonempty"),
        Index("ix_proposed_uses_project", "project_id"),
        Index("ix_proposed_uses_project_status", "project_id", "status"),
        Index("ix_proposed_uses_participant", "participant_id"),
        Index("ix_proposed_uses_story_element", "story_element_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    story_element_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("story_elements.id", ondelete="SET NULL"), nullable=True)
    use_type: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(128), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(256), nullable=True)
    territory: Mapped[str | None] = mapped_column(String(128), nullable=True)
    context_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default=text("'draft'"))
    proposed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)


class ProposedUseAnalysis(Base, CreatedAtMixin):
    __tablename__ = "proposed_use_analyses"
    __table_args__ = (
        CheckConstraint(f"outcome IN {in_clause(ANALYSIS_OUTCOMES)}", name="ck_analysis_outcome"),
        CheckConstraint("engine_version <> ''", name="ck_analysis_engine_version"),
        Index("ix_analyses_proposed_use", "proposed_use_id"),
        Index("ix_analyses_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    proposed_use_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("proposed_uses.id", ondelete="CASCADE"), nullable=False)
    # Denormalised for RLS tenancy scoping (set from the parent proposed use).
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    findings: Mapped[list] = mapped_column(JSONB, nullable=False)
    matched_consent_record_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'engine'"))
