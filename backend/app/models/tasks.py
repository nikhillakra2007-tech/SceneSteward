"""Tasks — human-owned work items (reviews, follow-ups, unresolved permissions,
agent-review duties, integration failure alerts)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import ACTOR_TYPES, TASK_PRIORITIES, TASK_STATUSES, TASK_TYPES, in_clause
from app.models.base import Base, TimestampMixin, uuid_pk


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(f"task_type IN {in_clause(TASK_TYPES)}", name="ck_tasks_type"),
        CheckConstraint(f"status IN {in_clause(TASK_STATUSES)}", name="ck_tasks_status"),
        CheckConstraint(f"priority IN {in_clause(TASK_PRIORITIES)}", name="ck_tasks_priority"),
        CheckConstraint(f"created_by_actor_type IN {in_clause(ACTOR_TYPES)}", name="ck_tasks_actor_type"),
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_owner_status", "owner_user_id", "status"),
        Index("ix_tasks_participant", "participant_id"),
        Index("ix_tasks_source", "source_type", "source_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=True)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'open'"))
    priority: Mapped[str] = mapped_column(String(12), nullable=False, server_default=text("'normal'"))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_actor_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'user'"))
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
