"""Reviews — human and agent review rows for a proposed use.

A human decision is a one-way transition recorded on the review row and in the
audit log; it is never derived from agent output alone.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import HUMAN_DECISIONS, REVIEW_STATUSES, REVIEWER_TYPES, in_clause
from app.models.base import Base, CreatedAtMixin, VersionMixin, uuid_pk


class Review(Base, CreatedAtMixin, VersionMixin):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(f"reviewer_type IN {in_clause(REVIEWER_TYPES)}", name="ck_reviews_reviewer_type"),
        CheckConstraint(f"review_status IN {in_clause(REVIEW_STATUSES)}", name="ck_reviews_status"),
        CheckConstraint(f"human_decision IS NULL OR human_decision IN {in_clause(HUMAN_DECISIONS)}", name="ck_reviews_decision"),
        CheckConstraint(
            "human_decision IS NULL OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)",
            name="ck_reviews_decision_actor",
        ),
        Index("ix_reviews_project", "project_id"),
        Index("ix_reviews_project_status", "project_id", "review_status"),
        Index("ix_reviews_proposed_use", "proposed_use_id"),
        Index("ix_reviews_reviewer", "reviewer_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    proposed_use_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("proposed_uses.id", ondelete="CASCADE"), nullable=False)
    reviewer_type: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    findings: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    evidence_references: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_decision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
