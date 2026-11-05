"""Participant schemas. Contact details travel via dedicated endpoints and are
encrypted at rest; they are never embedded in participant payloads."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import CONTACT_TYPES, PARTICIPANT_STATUSES
from app.schemas.common import ORMModel


class ParticipantCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    preferred_language: str | None = Field(default=None, max_length=64)
    preferred_contact_method: str | None = Field(default=None, max_length=64)
    accessibility_requirements: dict = Field(default_factory=dict)
    privacy_preferences: dict = Field(default_factory=dict)
    linked_user_id: uuid.UUID | None = None  # optional self-service account link


class ParticipantUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    preferred_language: str | None = Field(default=None, max_length=64)
    preferred_contact_method: str | None = Field(default=None, max_length=64)
    accessibility_requirements: dict | None = None
    privacy_preferences: dict | None = None
    participant_status: str | None = None
    expected_version: int = Field(ge=1)

    @field_validator("participant_status")
    @classmethod
    def _status_ok(cls, v: str | None) -> str | None:
        if v and v not in PARTICIPANT_STATUSES:
            raise ValueError(f"participant_status must be one of {PARTICIPANT_STATUSES}")
        return v


class ParticipantOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    display_name: str
    preferred_language: str | None
    preferred_contact_method: str | None
    accessibility_requirements: dict
    privacy_preferences: dict
    participant_status: str
    version: int
    created_at: datetime
    updated_at: datetime


class ContactRecordCreate(BaseModel):
    contact_type: str
    value: str = Field(min_length=3, max_length=500)  # plaintext in transit over TLS only; stored encrypted

    @field_validator("contact_type")
    @classmethod
    def _type_ok(cls, v: str) -> str:
        if v not in CONTACT_TYPES:
            raise ValueError(f"contact_type must be one of {CONTACT_TYPES}")
        return v


class ContactRecordOut(ORMModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    contact_type: str
    value: str  # decrypted only for authorised callers; never cached or logged
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConsentHistoryEntry(BaseModel):
    record_id: uuid.UUID
    version_number: int
    record_status: str
    participant_confirmation: str
    source_type: str
    confirmed_at: datetime | None
    created_at: datetime
    choice_count: int


class ParticipantTokenResponse(BaseModel):
    participant_id: uuid.UUID
    access_token: str
    portal_path: str
    expires_in_seconds: int
    token: str | None = None
    expires_in: int | None = None

    def model_post_init(self, context: object, /) -> None:
        if self.token is None:
            self.token = self.access_token
        if self.expires_in is None:
            self.expires_in = self.expires_in_seconds


class ClarificationRequestIn(BaseModel):
    concern: str = Field(min_length=3, max_length=5000)
    category: str | None = None
    contact_method: str | None = None
    request_type: str = Field(default="clarification", description="Type of request: clarification or withdrawal")


class ClarificationRequestOut(BaseModel):
    participant_id: uuid.UUID
    task_id: uuid.UUID
    status: str = "received"
    message: str

