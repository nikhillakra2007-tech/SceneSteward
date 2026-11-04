"""Integration events — idempotency and delivery bookkeeping for external systems.

payload_summary stores small non-sensitive metadata only, never raw documents
or credentials. external_event_id + integration_name is UNIQUE.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import INTEGRATION_PROCESSING_STATUSES, in_clause
from app.models.base import Base, CreatedAtMixin, uuid_pk


class IntegrationEvent(Base, CreatedAtMixin):
    __tablename__ = "integration_events"
    __table_args__ = (
        UniqueConstraint("integration_name", "external_event_id", name="uq_integration_events_external"),
        CheckConstraint(f"processing_status IN {in_clause(INTEGRATION_PROCESSING_STATUSES)}", name="ck_integration_status"),
        CheckConstraint("attempt_count >= 0", name="ck_integration_attempts"),
        Index("ix_integration_status_created", "processing_status", "created_at"),
        Index("ix_integration_correlation", "correlation_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    integration_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, server_default=text("gen_random_uuid()"))
    payload_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'received'"))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
