"""SSE listener for Switch agent events (run via scripts/switch_listener.py).

Security model:
  * Bearer agent API key; connection_id is a client-generated UUID reused on reconnect.
  * Every event is validated, deduplicated (integration_events unique constraint),
    and correlated to a project via switch_room_links.
  * NOTHING in this path can create, modify, or confirm consent records, reviews,
    or decisions. Findings are recorded for human review only.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import UTC
from typing import Any

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import IntegrationEvent, SwitchRoomLink

logger = logging.getLogger("scenesteward.switch.listener")


def external_event_id(raw: dict[str, Any]) -> str:
    seq = raw.get("sequence")
    if isinstance(seq, int):
        return f"seq:{seq}"
    if raw.get("event_id"):
        return str(raw["event_id"])
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest()
    return f"hash:{digest}"


def record_inbound_event(db: Session, raw: dict[str, Any]) -> tuple[str, uuid.UUID | None]:
    """Validate + persist an inbound event. Returns (status, event_uuid|None)."""
    from app.core.database import system_context
    with system_context():
        return _record_inbound_event(db, raw)


def _record_inbound_event(db: Session, raw: dict[str, Any]) -> tuple[str, uuid.UUID | None]:
    room_id = None
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if isinstance(data, dict):
        room_id = data.get("room_id") or (data.get("room") or {}).get("id")

    link = None
    if room_id:
        link = db.query(SwitchRoomLink).filter(SwitchRoomLink.switch_room_id == room_id).first()

    evt = IntegrationEvent(
        integration_name="switch",
        event_type=str(raw.get("type") or "unknown"),
        external_event_id=external_event_id(raw),
        project_id=link.project_id if link else None,
        payload_reference=f"room:{room_id}" if room_id else None,
        payload_summary={"type": raw.get("type"), "room_id": room_id,
                         "mapped_project_id": str(link.project_id) if link else None,
                         "mapped_participant_id": str(link.participant_id) if link and link.participant_id else None},
        processing_status="received",
    )
    try:
        with db.begin_nested():
            db.add(evt)
            db.flush()
    except IntegrityError:
        logger.info("duplicate switch event skipped id=%s", evt.external_event_id)
        return "skipped_duplicate", None

    if link is None:
        evt.processing_status = "processed"
        evt.last_error = "unmapped_room — recorded but not attached to any project"
    else:
        evt.processing_status = "processed"
    from datetime import datetime
    evt.processed_at = datetime.now(UTC)
    return "processed", evt.id


class SwitchEventListener:
    """Holds the agent SSE connection and forwards events to record_inbound_event."""

    def __init__(self, db_factory, *, connection_id: str | None = None,
                 max_backoff_seconds: int = 30, max_retries: int | None = None) -> None:
        self._db_factory = db_factory
        self.connection_id = connection_id or str(uuid.uuid4())
        self.max_backoff = max_backoff_seconds
        self.max_retries = max_retries
        s = get_settings()
        self.base = (s.switch_base_url or "").rstrip("/")
        self.agent_id = s.switch_agent_id
        self.api_key = s.switch_api_key

    def _stream(self):  # pragma: no cover - network path
        if not (self.base and self.agent_id and self.api_key):
            raise RuntimeError("Switch listener requires SWITCH_BASE_URL, SWITCH_AGENT_ID, SWITCH_API_KEY")
        params = {"connection_id": self.connection_id, "start_from": "head"}
        headers = {"Accept": "text/event-stream", "Authorization": f"Bearer {self.api_key}"}
        return httpx.stream("GET", f"{self.base}/agents/{self.agent_id}/events",
                            params=params, headers=headers, timeout=None)

    def handle_event(self, raw: dict[str, Any]) -> str:
        s = get_settings()
        if s.switch_adapter == "http":
            from app.integrations.switch.http_adapter import HttpSwitchAdapter
            if not HttpSwitchAdapter().validate_inbound_event(raw):
                logger.warning("invalid switch event rejected type=%s", raw.get("type"))
                return "invalid"
        db: Session = self._db_factory()
        try:
            status, _ = record_inbound_event(db, raw)
            db.commit()
            return status
        except Exception:
            db.rollback()
            logger.exception("failed to record switch event")
            return "error"
        finally:
            db.close()

    def run_forever(self) -> None:  # pragma: no cover - long-running network loop
        attempt = 0
        while True:
            try:
                with self._stream() as resp:
                    if resp.status_code in (401, 403):
                        logger.error("switch listener authentication failed (status=%s); stopping", resp.status_code)
                        return
                    resp.raise_for_status()
                    attempt = 0
                    for line in resp.iter_lines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        try:
                            raw = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            logger.warning("unparseable switch event line dropped")
                            continue
                        self.handle_event(raw)
            except KeyboardInterrupt:
                logger.info("switch listener stopped by operator")
                return
            except Exception:  # noqa: BLE001 — reconnect with bounded backoff, never crash the process
                attempt += 1
                if self.max_retries is not None and attempt > self.max_retries:
                    logger.error("switch listener giving up after %s attempts", attempt)
                    return
                delay = min(2 ** attempt, self.max_backoff)
                logger.warning("switch listener reconnecting in %ss (attempt %s)", delay, attempt)
                time.sleep(delay)
