"""Auth + user schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class MeResponse(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    auth_provider: str
    account_status: str
    last_login_at: datetime | None
    memberships: list[MembershipSummary] = Field(default_factory=list)


class MembershipSummary(ORMModel):
    project_id: uuid.UUID
    project_title: str
    role: str
    membership_status: str


class LogoutResponse(BaseModel):
    detail: str = Field(default="Client should discard the access token; provider sessions are managed by the auth provider.")
