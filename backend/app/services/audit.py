"""Audit trail service. Every state-changing operation records an event.

Audit writes happen inside the caller's transaction so the trail can never
disagree with the data it describes.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record(
    db: Session,
    *,
    project_id: uuid.UUID,
    participant_id: uuid.UUID | None,
    actor_type: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    previous_value: dict | None = None,
    new_value: dict | None = None,
    reason: str | None = None,
    correlation_id: uuid.UUID | None = None,
) -> AuditEvent:
    event = AuditEvent(
        project_id=project_id,
        participant_id=participant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=_redact(previous_value),
        new_value=_redact(new_value),
        reason=reason,
        correlation_id=correlation_id or uuid.uuid4(),
    )
    db.add(event)
    return event


def _redact(value: dict | None) -> dict | None:
    """Defence-in-depth: strip keys that must never appear in the audit trail."""
    if not value:
        return value
    blocked = ("password", "secret", "token", "api_key", "authorization", "encrypted_contact_data")
    return {k: ("[redacted]" if any(b in k.lower() for b in blocked) else v) for k, v in value.items()}


def actor_from_user(user: Any) -> tuple[str, str]:
    return "user", str(user.id)


def actor_agent(agent_name: str) -> tuple[str, str]:
    return "agent", agent_name


def actor_system() -> tuple[str, str]:
    return "system", "scenesteward"
