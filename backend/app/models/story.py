"""Story elements — the identifiable moments a production might use."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import SENSITIVITY_LEVELS, in_clause
from app.models.base import Base, TimestampMixin, VersionMixin, uuid_pk


class StoryElement(Base, TimestampMixin, VersionMixin):
    __tablename__ = "story_elements"
    __table_args__ = (
        CheckConstraint(f"sensitivity_level IN {in_clause(SENSITIVITY_LEVELS)}", name="ck_story_sensitivity"),
        CheckConstraint("title <> ''", name="ck_story_title_nonempty"),
        Index("ix_story_elements_project", "project_id"),
        Index("ix_story_elements_project_sensitivity", "project_id", "sensitivity_level"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    scene_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    identifying_details: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    sensitivity_level: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'standard'"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
