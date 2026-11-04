"""Proposed uses + comparison-engine output schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import PROPOSED_USE_STATUSES
from app.schemas.common import ORMModel


class ProposedUseCreate(BaseModel):
    participant_id: uuid.UUID
    story_element_id: uuid.UUID | None = None
    use_type: str = Field(min_length=1, max_length=64)
    platform: str | None = Field(default=None, max_length=128)
    audience: str | None = Field(default=None, max_length=128)
    purpose: str | None = Field(default=None, max_length=256)
    territory: str | None = Field(default=None, max_length=128)
    context_description: str | None = Field(default=None, max_length=10000)
    run_analysis: bool = True


class ProposedUseUpdate(BaseModel):
    use_type: str | None = Field(default=None, min_length=1, max_length=64)
    platform: str | None = Field(default=None, max_length=128)
    audience: str | None = Field(default=None, max_length=128)
    purpose: str | None = Field(default=None, max_length=256)
    territory: str | None = Field(default=None, max_length=128)
    context_description: str | None = Field(default=None, max_length=10000)
    status: str | None = None
    expected_version: int = Field(ge=1)

    @field_validator("status")
    @classmethod
    def _status_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in PROPOSED_USE_STATUSES:
            raise ValueError(f"status must be one of {PROPOSED_USE_STATUSES}")
        return v


class ProposedUseOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    participant_id: uuid.UUID
    story_element_id: uuid.UUID | None
    use_type: str
    platform: str | None
    audience: str | None
    purpose: str | None
    territory: str | None
    context_description: str | None
    status: str
    proposed_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class AnalysisFinding(BaseModel):
    category: str
    finding: str
    choice: str | None
    source_references: list[str]
    confidence: str
    uncertainty: str | None


class AnalysisOut(ORMModel):
    id: uuid.UUID
    proposed_use_id: uuid.UUID
    outcome: str
    findings: list[dict]
    matched_consent_record_ids: list[str]
    engine_version: str
    created_by_type: str
    created_at: datetime


class AnalyseResponse(BaseModel):
    proposed_use_id: uuid.UUID
    analysis: AnalysisOut
    outcome: str
    requires_human_review: bool
    tasks_created: list[uuid.UUID]
    review_id: uuid.UUID
