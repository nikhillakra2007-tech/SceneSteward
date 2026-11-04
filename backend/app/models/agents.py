"""Agent run records — full traceability of every AI/analysis invocation.

Raw sensitive document content is NOT stored here; input_reference points at the
source entity and output_data holds the validated, structured result.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import AGENT_NAMES, AGENT_RUN_STATUSES, in_clause
from app.models.base import Base, CreatedAtMixin, uuid_pk


class AgentRun(Base, CreatedAtMixin):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(f"agent_name IN {in_clause(AGENT_NAMES)}", name="ck_agent_runs_name"),
        CheckConstraint(f"execution_status IN {in_clause(AGENT_RUN_STATUSES)}", name="ck_agent_runs_status"),
        Index("ix_agent_runs_project_agent", "project_id", "agent_name"),
        Index("ix_agent_runs_proposed_use", "proposed_use_id"),
        Index("ix_agent_runs_status", "execution_status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=True)
    proposed_use_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("proposed_uses.id", ondelete="CASCADE"), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    input_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    execution_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'queued'"))
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
