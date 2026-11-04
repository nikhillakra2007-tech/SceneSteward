"""Review schemas; human decisions follow a validated state machine."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import HUMAN_DECISIONS, REVIEW_STATUSES
from app.schemas.common import ORMModel

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "completed", "cancelled"},
    "in_progress": {"completed", "escalated", "cancelled"},
    "completed": set(),   # terminal; a decision is required to enter it
    "escalated": {"in_progress", "completed", "cancelled"},
    "cancelled": set(),
}


class ReviewOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    proposed_use_id: uuid.UUID
    reviewer_type: str
    reviewer_id: uuid.UUID | None
    agent_name: str | None
    review_status: str
    findings: list[dict]
    evidence_references: list[dict]
    uncertainty: str | None
    human_decision: str | None
    decision_reason: str | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    completed_at: datetime | None
    version: int
    created_at: datetime


class HumanDecisionRequest(BaseModel):
    decision: str
    reason: str = Field(min_length=3, max_length=5000)
    expected_version: int = Field(ge=1)

    @field_validator("decision")
    @classmethod
    def _decision_ok(cls, v: str) -> str:
        if v not in HUMAN_DECISIONS:
            raise ValueError(f"decision must be one of {HUMAN_DECISIONS}")
        return v


class RequestDiscussionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)
    expected_version: int = Field(ge=1)


class ResolveRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class ReviewListQuery(BaseModel):
    review_status: str | None = None

    @field_validator("review_status")
    @classmethod
    def _status_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in REVIEW_STATUSES:
            raise ValueError(f"review_status must be one of {REVIEW_STATUSES}")
        return v
