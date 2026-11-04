"""Participant communication schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import COMMUNICATION_TYPES
from app.schemas.common import ORMModel


class CommunicationOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    participant_id: uuid.UUID
    communication_type: str
    subject: str | None
    draft_content: str | None
    communication_status: str
    created_by: uuid.UUID
    approved_by: uuid.UUID | None
    sent_at: datetime | None
    created_at: datetime


class CommunicationCreate(BaseModel):
    participant_id: uuid.UUID
    communication_type: str = "email"
    subject: str | None = Field(default=None, max_length=300)
    draft_content: str | None = Field(default=None, max_length=10000)

    @field_validator("communication_type")
    @classmethod
    def _type_ok(cls, v: str) -> str:
        if v not in COMMUNICATION_TYPES:
            raise ValueError(f"communication_type must be one of {COMMUNICATION_TYPES}")
        return v


class CommunicationApprove(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)

