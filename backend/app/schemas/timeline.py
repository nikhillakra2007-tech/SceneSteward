"""Tasks, timeline, and integration-status schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.choices import TASK_PRIORITIES, TASK_STATUSES
from app.schemas.common import ORMModel


class TaskOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    participant_id: uuid.UUID | None
    task_type: str
    title: str
    description: str | None
    status: str
    priority: str
    owner_user_id: uuid.UUID | None
    source_type: str | None
    source_id: uuid.UUID | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class TaskUpdate(BaseModel):
    status: str | None = None
    owner_user_id: uuid.UUID | None = None
    due_at: datetime | None = None
    priority: str | None = None

    @field_validator("status")
    @classmethod
    def _status_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in TASK_STATUSES:
            raise ValueError(f"status must be one of {TASK_STATUSES}")
        return v

    @field_validator("priority")
    @classmethod
    def _priority_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {TASK_PRIORITIES}")
        return v


class TimelineEntry(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    actor_type: str
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    reason: str | None
    correlation_id: uuid.UUID
    participant_id: uuid.UUID | None


class IntegrationStatus(BaseModel):
    name: str
    status: str  # configured_verified | configured_unverified | unavailable | missing_credentials | failed_authentication | timeout
    detail: str | None = None


class IntegrationHealthResponse(BaseModel):
    integrations: list[IntegrationStatus]
