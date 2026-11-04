"""Accountability timeline — keyset-paginated audit feed with role filtering."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import SENSITIVE_ENTITY_TYPES, VIEWER
from app.models import AuditEvent

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def encode_cursor(ts: datetime, event_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(json.dumps({"ts": ts.isoformat(), "id": str(event_id)}).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    return datetime.fromisoformat(raw["ts"]), uuid.UUID(raw["id"])


def timeline_query(
    db: Session,
    *,
    project_id: uuid.UUID,
    participant_id: uuid.UUID | None,
    viewer_role: str,
    limit: int,
    cursor: str | None,
) -> tuple[list[AuditEvent], str | None]:
    limit = max(1, min(limit, MAX_LIMIT))
    stmt = select(AuditEvent).where(AuditEvent.project_id == project_id)
    if participant_id is not None:
        stmt = stmt.where(AuditEvent.participant_id == participant_id)
    if viewer_role == VIEWER:
        stmt = stmt.where(AuditEvent.entity_type.notin_(tuple(SENSITIVE_ENTITY_TYPES)))
    if cursor:
        ts, eid = decode_cursor(cursor)
        stmt = stmt.where(
            (AuditEvent.timestamp < ts) | ((AuditEvent.timestamp == ts) & (AuditEvent.id < eid))
        )
    stmt = stmt.order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc()).limit(limit + 1)
    rows = list(db.execute(stmt).scalars().all())
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = encode_cursor(last.timestamp, last.id)
        rows = rows[:limit]
    return rows, next_cursor
