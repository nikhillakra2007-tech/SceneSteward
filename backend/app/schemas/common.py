"""Shared schema primitives."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    next_cursor: str | None = None


class Timestamped(ORMModel):
    created_at: datetime
    updated_at: datetime | None = None


class IdResponse(BaseModel):
    id: uuid.UUID


class ExpectedVersion(BaseModel):
    expected_version: int = Field(ge=1)
