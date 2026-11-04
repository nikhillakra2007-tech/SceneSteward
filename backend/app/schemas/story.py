"""Story element schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.choices import SENSITIVITY_LEVELS
from app.schemas.common import ORMModel


class StoryElementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    scene_reference: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=10000)
    identifying_details: list[str] = Field(default_factory=list, max_length=50)
    sensitivity_level: str = "standard"

    @field_validator("sensitivity_level")
    @classmethod
    def _sens_ok(cls, v: str) -> str:
        if v not in SENSITIVITY_LEVELS:
            raise ValueError(f"sensitivity_level must be one of {SENSITIVITY_LEVELS}")
        return v


class StoryElementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    scene_reference: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=10000)
    identifying_details: list[str] | None = None
    sensitivity_level: str | None = None
    expected_version: int = Field(ge=1)

    @field_validator("sensitivity_level")
    @classmethod
    def _sens_ok(cls, v: str | None) -> str | None:
        if v is not None and v not in SENSITIVITY_LEVELS:
            raise ValueError(f"sensitivity_level must be one of {SENSITIVITY_LEVELS}")
        return v


class StoryElementOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    scene_reference: str | None
    description: str | None
    identifying_details: list[str]
    sensitivity_level: str
    created_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime
