"""SQLAlchemy declarative base and shared column helpers."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
        onupdate=text("now()"),
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class VersionMixin:
    """Optimistic-locking counter; every write path checks expected_version."""
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))


def fk(column_name: str, target: str, *, on_delete: str = "CASCADE", nullable: bool = False):
    from sqlalchemy import ForeignKey  # local import to keep module import light
    return mapped_column(UUID(as_uuid=True), ForeignKey(target, ondelete=on_delete), nullable=nullable)
