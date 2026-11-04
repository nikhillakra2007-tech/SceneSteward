"""Release documents (signed releases) and their extracted text pages."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.choices import EXTRACTION_STATUSES, SIGNATURE_STATUSES, in_clause
from app.models.base import Base, CreatedAtMixin, uuid_pk


class ReleaseDocument(Base, CreatedAtMixin):
    __tablename__ = "release_documents"
    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_release_documents_storage_key"),
        CheckConstraint(f"signature_status IN {in_clause(SIGNATURE_STATUSES)}", name="ck_documents_signature_status"),
        CheckConstraint(f"extraction_status IN {in_clause(EXTRACTION_STATUSES)}", name="ck_documents_extraction_status"),
        CheckConstraint("file_size > 0 AND file_size <= 52428800", name="ck_documents_file_size"),
        Index("ix_documents_participant", "participant_id"),
        Index("ix_documents_project", "project_id"),
        Index("ix_documents_extraction_status", "extraction_status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    signature_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'unknown'"))
    extraction_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)


class DocumentPage(Base, CreatedAtMixin):
    """Extracted text with page references. Private; never exposed in logs."""
    __tablename__ = "release_document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_doc_page"),
        Index("ix_document_pages_document", "document_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("release_documents.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
