"""Release document schemas (private storage; signed upload/download URLs)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import SIGNATURE_STATUSES
from app.schemas.common import ORMModel

ALLOWED_UPLOAD_MIMES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


class UploadUrlRequest(BaseModel):
    original_filename: str = Field(min_length=1, max_length=255)
    mime_type: str
    file_size: int = Field(gt=0)
    document_date: date | None = None
    signature_status: str = "unknown"

    @field_validator("mime_type")
    @classmethod
    def _mime_ok(cls, v: str) -> str:
        if v not in ALLOWED_UPLOAD_MIMES:
            raise ValueError(f"mime_type must be one of {sorted(ALLOWED_UPLOAD_MIMES)}")
        return v

    @field_validator("signature_status")
    @classmethod
    def _sig_ok(cls, v: str) -> str:
        if v not in SIGNATURE_STATUSES:
            raise ValueError(f"signature_status must be one of {SIGNATURE_STATUSES}")
        return v


class UploadUrlResponse(BaseModel):
    storage_key: str
    upload_url: str
    expires_in_seconds: int
    max_upload_bytes: int


class CompleteUploadRequest(BaseModel):
    storage_key: str = Field(min_length=8, max_length=1024)
    document_date: date | None = None
    signature_status: str = "unknown"


class DocumentOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    participant_id: uuid.UUID
    storage_key: str
    original_filename: str
    mime_type: str
    file_size: int
    document_date: date | None
    signature_status: str
    extraction_status: str
    extraction_error: str | None
    uploaded_by: uuid.UUID
    created_at: datetime


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in_seconds: int


class AdversarialFlagOut(BaseModel):
    category: str
    snippet: str
    page_number: int
    remediation: str


class DetectedClauseOut(BaseModel):
    category: str
    choice_indication: str
    quote: str
    page_number: int
    line_number: int
    confidence: float
    explanation: str


class StatedExclusionOut(BaseModel):
    quote: str
    page_number: int
    targeted_category: str | None


class DocumentIntelligenceOut(BaseModel):
    document_id: str
    total_pages: int
    content_hash: str
    adversarial_flags: list[AdversarialFlagOut]
    detected_clauses: list[DetectedClauseOut]
    stated_exclusions: list[StatedExclusionOut]
    unmentioned_categories: list[str]
    advisory_notice: str
