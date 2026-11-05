"""Project and membership schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import MEMBERSHIP_ROLES, MEMBERSHIP_STATUSES, PROJECT_STATUSES
from app.schemas.common import ORMModel


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    purpose: str | None = Field(default=None, max_length=5000)
    themes: list[str] = Field(default_factory=list, max_length=30)
    intended_audiences: list[str] = Field(default_factory=list, max_length=30)
    distribution_plan: str | None = Field(default=None, max_length=5000)

    @field_validator("themes", "intended_audiences")
    @classmethod
    def _strip_items(cls, v: list[str]) -> list[str]:
        cleaned = [item.strip()[:80] for item in v if item and item.strip()]
        return cleaned[:30]


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    purpose: str | None = Field(default=None, max_length=5000)
    themes: list[str] | None = None
    intended_audiences: list[str] | None = None
    distribution_plan: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    expected_version: int = Field(ge=1)

    @field_validator("status")
    @classmethod
    def _status_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {PROJECT_STATUSES}")
        return v


class ProjectOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None
    purpose: str | None
    themes: list[str]
    intended_audiences: list[str]
    distribution_plan: str | None
    status: str
    created_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class MemberOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    email: str | None = None
    full_name: str | None = None
    role: str
    membership_status: str
    invited_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: str
    membership_status: str = "active"

    @field_validator("role")
    @classmethod
    def _role_ok(cls, v: str) -> str:
        if v not in MEMBERSHIP_ROLES:
            raise ValueError(f"role must be one of {MEMBERSHIP_ROLES}")
        return v

    @field_validator("membership_status")
    @classmethod
    def _status_ok(cls, v: str) -> str:
        if v not in MEMBERSHIP_STATUSES:
            raise ValueError(f"membership_status must be one of {MEMBERSHIP_STATUSES}")
        return v


class MemberUpdate(BaseModel):
    role: str | None = None
    membership_status: str | None = None

    @field_validator("role")
    @classmethod
    def _role_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in MEMBERSHIP_ROLES:
            raise ValueError(f"role must be one of {MEMBERSHIP_ROLES}")
        return v

    @field_validator("membership_status")
    @classmethod
    def _status_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in MEMBERSHIP_STATUSES:
            raise ValueError(f"membership_status must be one of {MEMBERSHIP_STATUSES}")
        return v


class NotificationOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    notification_type: str
    title: str
    message: str
    priority: str
    entity_type: str
    entity_id: uuid.UUID | None
    created_at: datetime


class ProjectAuditExportOut(BaseModel):
    project_id: uuid.UUID
    project_title: str
    purpose: str | None
    generated_at: datetime
    total_participants: int
    participant_summary: dict[str, int]
    consent_overview: dict[str, dict[str, int]]
    pending_tasks_count: int
    urgent_tasks_count: int
    audit_events_count: int
    compliance_status: str
    invariants_verified: list[str]
    integrity_hash: str
