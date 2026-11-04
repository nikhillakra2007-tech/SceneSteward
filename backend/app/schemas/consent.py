"""Consent schemas. Confirmed records are effectively immutable: changes create
a new version. There is intentionally no bulk-update endpoint."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import (
    CONSENT_CATEGORIES,
    CONSENT_CHOICES,
    SOURCE_TYPES,
)
from app.schemas.common import ORMModel


class ConsentChoiceIn(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    choice: str
    explanation: str | None = Field(default=None, max_length=2000)
    evidence_reference: str | None = Field(default=None, max_length=500)
    source_type: str = "manual"
    confidence_if_extracted: float | None = Field(default=None, ge=0, le=1)

    @field_validator("choice")
    @classmethod
    def _choice_ok(cls, v: str) -> str:
        if v not in CONSENT_CHOICES:
            raise ValueError(f"choice must be one of {CONSENT_CHOICES}")
        return v

    @field_validator("source_type")
    @classmethod
    def _source_ok(cls, v: str) -> str:
        if v not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {SOURCE_TYPES}")
        return v

    @field_validator("category")
    @classmethod
    def _category_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("category must not be empty")
        return v


class ConsentChoiceOut(ORMModel):
    id: uuid.UUID
    category: str
    choice: str
    explanation: str | None
    evidence_reference: str | None
    source_type: str
    confidence_if_extracted: float | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    created_at: datetime


class ConsentRecordCreate(BaseModel):
    source_type: str
    source_document_id: uuid.UUID | None = None
    explanation: str | None = Field(default=None, max_length=5000)
    choices: list[ConsentChoiceIn] = Field(min_length=1, max_length=100)

    @field_validator("source_type")
    @classmethod
    def _source_ok(cls, v: str) -> str:
        if v not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {SOURCE_TYPES}")
        return v

    @field_validator("choices")
    @classmethod
    def _unique_categories(cls, v: list[ConsentChoiceIn]) -> list[ConsentChoiceIn]:
        seen: set[str] = set()
        for c in v:
            if c.category in seen:
                raise ValueError(f"duplicate category in record: {c.category}")
            seen.add(c.category)
        return v


class ConsentRecordOut(ORMModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    project_id: uuid.UUID
    version_number: int
    record_status: str
    source_type: str
    source_document_id: uuid.UUID | None
    explanation: str | None
    recorded_by: uuid.UUID
    participant_confirmation: str
    confirmed_at: datetime | None
    version: int
    created_at: datetime
    choices: list[ConsentChoiceOut]


class ConsentConfirmRequest(BaseModel):
    confirmation: str  # 'confirmed' | 'declined' | 'partial'
    confirmation_evidence: str = Field(min_length=3, max_length=1000)  # e.g. "signed page 2 of release form #A-17"
    expected_version: int = Field(ge=1)

    @field_validator("confirmation")
    @classmethod
    def _confirmation_ok(cls, v: str) -> str:
        if v not in ("confirmed", "declined", "partial"):
            raise ValueError("confirmation must be one of confirmed|declined|partial")
        return v


class ConsentHistoryOut(BaseModel):
    records: list[ConsentRecordOut]


CANONICAL_CATEGORIES = CONSENT_CATEGORIES
