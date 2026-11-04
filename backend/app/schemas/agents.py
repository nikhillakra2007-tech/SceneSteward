"""Agent-run schemas and the structured agent output contract (validated on ingest)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.choices import AGENT_NAMES
from app.schemas.common import ORMModel

Confidence = Literal["low", "medium", "high"]


class AgentRequest(BaseModel):
    agent_name: str
    proposed_use_id: uuid.UUID

    @field_validator("agent_name")
    @classmethod
    def _agent_ok(cls, v: str) -> str:
        if v not in AGENT_NAMES:
            raise ValueError(f"agent_name must be one of {AGENT_NAMES}")
        return v


class AgentFinding(BaseModel):
    category: str | None = Field(default=None, max_length=100)
    finding: str = Field(min_length=1, max_length=2000)
    choice: str | None = Field(default=None, max_length=32)
    source_references: list[str] = Field(default_factory=list, max_length=50)
    confidence: Confidence = "medium"
    uncertainty: str | None = Field(default=None, max_length=1000)


class AgentOutput(BaseModel):
    agent: str
    run_id: uuid.UUID
    project_id: uuid.UUID
    participant_id: uuid.UUID | None
    proposed_use_id: uuid.UUID | None
    result: Literal["RECORDED_CHOICE_MATCH", "NEEDS_DISCUSSION", "PARTICIPANT_DECLINED", "HUMAN_REVIEW_REQUIRED", "UNRESOLVED"]
    findings: list[AgentFinding]
    recommended_actions: list[str] = Field(default_factory=list, max_length=50)
    requires_human_review: bool = True


class AgentRunOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    participant_id: uuid.UUID | None
    proposed_use_id: uuid.UUID | None
    agent_name: str
    model_provider: str
    model_version: str | None
    prompt_version: str | None
    execution_status: str
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AgentRunDetailOut(AgentRunOut):
    output_data: dict | None
    input_reference: str | None


class AgentFindingOut(BaseModel):
    agent_name: str
    run_id: uuid.UUID
    execution_status: str
    output_data: dict | None
    created_at: datetime
