"""Projects and project memberships."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.choices import MEMBERSHIP_ROLES, MEMBERSHIP_STATUSES, PROJECT_STATUSES, in_clause
from app.models.base import Base, TimestampMixin, VersionMixin, uuid_pk


class Project(Base, TimestampMixin, VersionMixin):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(f"status IN {in_clause(PROJECT_STATUSES)}", name="ck_projects_status"),
        CheckConstraint("title <> ''", name="ck_projects_title_nonempty"),
        CheckConstraint("length(title) <= 200", name="ck_projects_title_len"),
        Index("ix_projects_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    themes: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    intended_audiences: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    distribution_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    memberships: Mapped[list[ProjectMembership]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMembership(Base, TimestampMixin):
    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_memberships_project_user"),
        CheckConstraint(f"role IN {in_clause(MEMBERSHIP_ROLES)}", name="ck_memberships_role"),
        CheckConstraint(f"membership_status IN {in_clause(MEMBERSHIP_STATUSES)}", name="ck_memberships_status"),
        Index("ix_memberships_user", "user_id"),
        Index("ix_memberships_project_status", "project_id", "membership_status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    membership_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    invited_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    project: Mapped[Project] = relationship(back_populates="memberships")
