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
import threading
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


def _extract_room_id(raw: dict[str, Any]) -> str | None:
    if isinstance(raw.get("room_id"), str):
        return raw["room_id"]
    data = raw.get("data") if isinstance(raw.get("data"), dict) else None
    if isinstance(data, dict):
        room_id = data.get("room_id") or (data.get("room") or {}).get("id")
        if room_id:
            return str(room_id)
    return None


def external_event_id(raw: dict[str, Any]) -> str:
    seq = raw.get("sequence")
    if isinstance(seq, int):
        return f"seq:{seq}"
    if raw.get("event_id"):
        return str(raw["event_id"])
    # Real AgentEvent (poll and SSE): payload.message_id is the stable message key
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else None
    if isinstance(payload, dict) and payload.get("message_id"):
        return f"msg:{payload['message_id']}"
    data = raw.get("data") if isinstance(raw.get("data"), dict) else None
    if isinstance(data, dict) and data.get("id"):
        return str(data["id"])
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest()
    return f"hash:{digest}"


def record_inbound_event(db: Session, raw: dict[str, Any]) -> tuple[str, uuid.UUID | None]:
    """Validate + persist an inbound event. Returns (status, event_uuid|None)."""
    from app.core.database import system_context
    with system_context():
        return _record_inbound_event(db, raw)


def _record_inbound_event(db: Session, raw: dict[str, Any]) -> tuple[str, uuid.UUID | None]:
    room_id = _extract_room_id(raw)

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
        self._generation: int | None = None
        self._beating = False
        self._beat_thread: threading.Thread | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _beat_once(self) -> None:
        """Refresh the SSE connection lease (server evicts after ~2s without a beat)."""
        if not (self.base and self.agent_id):
            return
        body: dict[str, Any] = {"connection_id": self.connection_id}
        if self._generation is not None:
            body["generation"] = self._generation
        try:
            httpx.post(f"{self.base}/agents/{self.agent_id}/connection/beat",
                       json=body, headers=self._headers(), timeout=5.0)
        except httpx.HTTPError:
            logger.debug("switch connection beat failed", exc_info=True)

    def _beat_loop(self) -> None:
        while self._beating:
            self._beat_once()
            time.sleep(2.0)

    def _start_beating(self) -> None:
        if self._beating:
            return
        self._beating = True
        self._beat_thread = threading.Thread(target=self._beat_loop, daemon=True, name="switch-beat")
        self._beat_thread.start()

    def _stop_beating(self) -> None:
        self._beating = False
        thread = self._beat_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)
        self._beat_thread = None

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
        session_or_factory = self._db_factory()
        if callable(session_or_factory) and not hasattr(session_or_factory, "begin_nested"):
            db: Session = session_or_factory()
        else:
            db = session_or_factory
        try:
            status, _ = record_inbound_event(db, raw)
            db.commit()

            # Dispatch only first-time message events. A duplicate delivery must never
            # re-trigger the worker (no duplicate assessments in the room).
            if status == "processed" and raw.get("type") == "message":
                try:
                    from app.integrations.switch.agent_worker import SwitchAgentWorker
                    worker = SwitchAgentWorker()
                    worker.process_room_message(db, raw)
                except Exception:
                    logger.exception("error processing switch room message in agent worker")

            return status
        except Exception:
            db.rollback()
            logger.exception("failed to record switch event")
            return "error"
        finally:
            db.close()

    def run_poll_forever(self, *, poll_timeout: float = 20.0) -> None:  # pragma: no cover - network loop
        """Long-poll the agent event buffer. No heartbeat needed; 204 == empty queue.

        This is the contract-stable receive path (the SSE stream is a compatibility
        window that requires a beat every 2s and a room claim).
        """
        while True:
            try:
                resp = httpx.get(
                    f"{self.base}/agents/{self.agent_id}/events",
                    params={"timeout": poll_timeout},
                    headers=self._headers(),
                    timeout=poll_timeout + 15,
                )
                if resp.status_code == 204:
                    continue
                if resp.status_code in (401, 403):
                    logger.error("switch listener authentication failed (status=%s); stopping", resp.status_code)
                    return
                if resp.status_code != 200:
                    logger.warning("switch poll returned %s", resp.status_code)
                    time.sleep(3)
                    continue
                try:
                    payload = resp.json()
                except ValueError:
                    logger.warning("switch poll returned non-JSON")
                    continue
                events = payload.get("events", []) if isinstance(payload, dict) else []
                for raw in events:
                    if not isinstance(raw, dict):
                        continue
                    if raw.get("type") in {"connection_state", "evicted", "gap", "subscription_changed"}:
                        continue
                    self.handle_event(raw)
            except KeyboardInterrupt:
                logger.info("switch listener stopped by operator")
                return
            except Exception:
                logger.warning("switch poll error; retrying in 3s", exc_info=True)
                time.sleep(3)

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
                    self._start_beating()
                    for line in resp.iter_lines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        try:
                            raw = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            logger.warning("unparseable switch event line dropped")
                            continue
                        if not isinstance(raw, dict):
                            continue
                        frame_type = raw.get("type")
                        if frame_type == "connection_state":
                            gen = raw.get("generation")
                            if isinstance(gen, int):
                                self._generation = gen
                            continue
                        if frame_type == "evicted":
                            logger.warning("switch listener evicted: %s", raw.get("reason"))
                            break
                        if frame_type in {"gap", "subscription_changed"}:
                            logger.info("switch control frame: %s", frame_type)
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
            finally:
                self._stop_beating()
