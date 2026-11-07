"""Actual Switch Connection Bridge — hardened to the real Switch Core contract.

Connects SceneSteward's backend to the real Switch Core server running
on the local machine (managed by Switch Console), rather than the
local simulator on port 8010.

Switch Core wire contract (handlers.py + protocol/types.py, Core 0.31.0):
- Health:           GET  /health                         -> 200 {"status":"ok"}
- Ops discovery:    GET  /agents/{id}/ops               -> 200 {"operations": {...}}
- Ops call:         POST /agents/{id}/ops/{operation}   -> 200 {"result": ...}
- Post message:     POST /agents/{id}/message           {room_id, content}
                                                              -> 200 {"ok": true, "event_id": "sw_..."}
- Agent events (long poll): GET /agents/{id}/events?timeout=<s>
    * no Accept: text/event-stream -> long poll. 204 No Content == empty queue
      (valid); 200 {"events": [AgentEvent, ...]} == events available (consumes).
- Agent events (SSE/stream): GET /agents/{id}/events?connection_id=<uuid>&start_from=head
      with Accept: text/event-stream. Frames are `event: <type>` + `data: <AgentEvent JSON>`
      plus `id: <sequence|ticket>`; keepalive is `: keepalive`. Requires POST
      /agents/{id}/connection/beat and room claims via /connection/subscribe.
- Room events (long poll): GET /agents/{id}/rooms/{room_id}/events?timeout=<s> (same 204/200)
- Notifications (addressed only): GET /agents/{id}/notifications?timeout=<s>
- History:          GET  /agents/{id}/rooms/{room_id}/history?limit=N
                                                              -> 200 {"events": [{sender, sender_name, body, timestamp}], "has_more": bool}
- Participants:     GET  /agents/rooms/{room_id}/participants
                                                              -> 200 {"participants": [{type, agent_id, name, status}]}

AgentEvent shape (protocol/types.py):
  { "type": "message" | "command" | "room_join",
    "room_id": str, "bridge_id": str|None, "channel_type": str|None,
    "payload": { MessagePayload | CommandPayload | RoomJoinPayload } }
MessagePayload: { addressed, sender, sender_name, sender_kind ("user"|"agent"|"platform"|None),
  message_id, body, timestamp, thread_id, attachments, ... }
SSE data is the AgentEvent JSON plus optional top-level `sequence` (own events)
or `position` (conversation), `missed`. Dedup key is payload.message_id,
falling back to sequence / event_id / content hash.

Credentials:
  - Switch Core API: http://localhost:64432
  - Agent ID: adf16e2a-4ce2-4598-baa7-ca8865ca4308
  - Room ID: aeec10b9-781c-4625-a07a-692279393943
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

import httpx

logger = logging.getLogger("scenesteward.actual_switch")


def canonical_event_id(event: dict[str, Any]) -> str:
    """Dedupe key covering both real AgentEvent and legacy simulator shapes."""
    seq = event.get("sequence")
    if isinstance(seq, int):
        return f"seq:{seq}"
    if event.get("event_id"):
        return str(event["event_id"])
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else None
    if isinstance(payload, dict) and payload.get("message_id"):
        return f"msg:{payload['message_id']}"
    data = event.get("data") if isinstance(event.get("data"), dict) else None
    if isinstance(data, dict) and data.get("id"):
        return str(data["id"])
    digest = hashlib.sha256(json.dumps(event, sort_keys=True, default=str).encode()).hexdigest()
    return f"hash:{digest}"


def event_type(event: dict[str, Any]) -> str:
    return str(event.get("type") or "unknown")


def is_message_event(event: dict[str, Any]) -> bool:
    return event_type(event) == "message"


class ActualSwitchBridge:
    """Bridge connecting SceneSteward to the actual Switch Core server.

    Poll mode (default) uses the long-poll endpoints (200/204). SSE streaming
    mode is available via :meth:`start_sse_listener` for low-latency delivery;
    both share the same dedupe/validation/handlers. No FastAPI event-loop
    blocking: all network waits run in daemon threads with explicit timeouts.
    """

    def __init__(
        self,
        switch_url: str = "http://localhost:64432",
        agent_api_key: str = "IYaYTuAw1OU_SdPuUEEUqDPJ4fJp2WJjmysz5Gv-F1c",
        agent_id: str = "adf16e2a-4ce2-4598-baa7-ca8865ca4308",
        room_id: str = "aeec10b9-781c-4625-a07a-692279393943",
        poll_timeout: float = 5.0,
        poll_interval: float = 2.0,
    ) -> None:
        self.switch_url = switch_url.rstrip("/")
        self.agent_api_key = agent_api_key
        self.agent_id = agent_id
        self.room_id = room_id
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self._running = False
        self._listener_thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._message_handlers: list[Callable[[dict[str, Any]], Any]] = []
        self.connection_id = str(uuid.uuid4())

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.agent_api_key}",
            "Content-Type": "application/json",
        }

    # ── Lifecycle ──

    def health_check(self) -> bool:
        """Verify the actual Switch Core server is reachable."""
        try:
            r = httpx.get(f"{self.switch_url}/health", timeout=5)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except Exception:  # noqa: BLE001
            return False

    def start_listener(self) -> bool:
        """Start polling for events from the actual Switch server."""
        if not self.health_check():
            logger.error("Actual Switch Core not reachable at %s", self.switch_url)
            return False
        if self._running:
            return True
        self._running = True
        self._listener_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="actual-switch-listener"
        )
        self._listener_thread.start()
        logger.info(
            "Actual Switch listener started (agent=%s, room=%s)",
            self.agent_id,
            self.room_id,
        )
        return True

    def start_sse_listener(self) -> bool:
        """Start SSE streaming listener (needs connection_id + heartbeats)."""
        if not self.health_check():
            logger.error("Actual Switch Core not reachable at %s", self.switch_url)
            return False
        if self._running:
            return True
        self._running = True
        self._listener_thread = threading.Thread(
            target=self._sse_loop, daemon=True, name="actual-switch-sse"
        )
        self._listener_thread.start()
        logger.info("Actual Switch SSE listener started (connection_id=%s)", self.connection_id)
        return True

    def stop(self) -> None:
        """Graceful shutdown: stop loops; threads are daemons so no hang."""
        self._running = False
        logger.info("Actual Switch listener stopped")

    def on_message(self, handler) -> None:
        """Register a callback for incoming messages."""
        self._message_handlers.append(handler)

    # ── Messaging ──

    def send_message(self, content: str, room_id: str | None = None) -> dict:
        """Send a message to a Switch room as the SceneSteward agent."""
        target_room = room_id or self.room_id
        payload = {"room_id": target_room, "content": content}
        try:
            r = httpx.post(
                f"{self.switch_url}/agents/{self.agent_id}/message",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            try:
                result = r.json()
            except Exception:  # noqa: BLE001
                result = {}
            logger.info("Message sent to actual Switch room %s: %s", target_room, r.status_code)
            if r.status_code == 200 and result.get("ok", True):
                return {"ok": True, "event_id": result.get("event_id"), "status": r.status_code}
            detail = result.get("detail") or r.text[:300]
            logger.warning("Switch message post failed status=%s detail=%s", r.status_code, detail[:200])
            return {"ok": False, "event_id": result.get("event_id"), "status": r.status_code, "error": str(detail)}
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to send message to actual Switch: %s", e)
            return {"ok": False, "error": str(e)}

    # ── Event polling ──

    def _get_events(self, path: str, *, timeout: float | None = None) -> list[dict]:
        """Long-poll helper: 204 == empty queue (valid), 200 == events."""
        try:
            r = httpx.get(
                f"{self.switch_url}{path}",
                headers=self._headers,
                timeout=(timeout or self.poll_timeout) + 10,
            )
            if r.status_code == 204:
                return []
            if r.status_code != 200:
                logger.debug("Poll %s returned %s", path, r.status_code)
                return []
            try:
                data = r.json()
            except Exception:  # noqa: BLE001
                return []
            events = data.get("events", [])
            return events if isinstance(events, list) else []
        except Exception as e:  # noqa: BLE001
            logger.debug("Event poll failed for %s: %s", path, e)
            return []

    def poll_events(self, *, timeout: float | None = None) -> list[dict]:
        """Poll for new events across all agent rooms (consumes legacy:all reader)."""
        t = timeout if timeout is not None else self.poll_timeout
        return self._get_events(
            f"/agents/{self.agent_id}/events?timeout={t}", timeout=t
        )

    def poll_room_events(self, room_id: str | None = None, *, timeout: float | None = None) -> list[dict]:
        """Poll for events in a single room (dedicated legacy:room reader)."""
        target = room_id or self.room_id
        t = timeout if timeout is not None else self.poll_timeout
        return self._get_events(
            f"/agents/{self.agent_id}/rooms/{target}/events?timeout={t}", timeout=t
        )

    def poll_notifications(self, *, timeout: float | None = None) -> list[dict]:
        """Poll addressed notifications only (never drains room conversation)."""
        t = timeout if timeout is not None else self.poll_timeout
        return self._get_events(
            f"/agents/{self.agent_id}/notifications?timeout={t}", timeout=t
        )

    def list_rooms(self) -> list[dict]:
        """List rooms this agent is a member of."""
        try:
            r = httpx.get(
                f"{self.switch_url}/agents/{self.agent_id}/moderation/rooms",
                headers=self._headers,
                timeout=10,
            )
            if r.status_code == 200:
                return r.json().get("rooms", [])
            return []
        except Exception:  # noqa: BLE001
            return []

    def list_participants(self, room_id: str | None = None) -> list[dict]:
        """List room participants (correct /agents/rooms path)."""
        target = room_id or self.room_id
        try:
            r = httpx.get(
                f"{self.switch_url}/agents/rooms/{target}/participants",
                headers=self._headers,
                timeout=10,
            )
            if r.status_code == 200:
                return r.json().get("participants", [])
            return []
        except Exception:  # noqa: BLE001
            return []

    def get_room_history(self, room_id: str | None = None) -> list[dict]:
        """Get message history for a room."""
        target = room_id or self.room_id
        try:
            r = httpx.get(
                f"{self.switch_url}/agents/{self.agent_id}/rooms/{target}/history",
                headers=self._headers,
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                # HistoryResponse is {"events": [...], "has_more": bool}; legacy tolerated "messages"
                ev = data.get("events", data.get("messages", []))
                return ev if isinstance(ev, list) else []
            return []
        except Exception:  # noqa: BLE001
            return []

    def _dispatch(self, event: dict[str, Any]) -> bool:
        """Dedupe + validate + fan out. Returns True if accepted (not duplicate)."""
        if not isinstance(event, dict) or not event.get("type"):
            return False
        if event.get("type") in {"connection_state", "gap", "evicted", "subscription_changed"}:
            return False
        eid = canonical_event_id(event)
        if eid in self._processed:
            logger.info("duplicate actual-switch event skipped id=%s", eid)
            return False
        if eid:
            self._processed.add(eid)
        if is_message_event(event):
            for handler in self._message_handlers:
                try:
                    handler(event)
                except Exception as e:  # noqa: BLE001
                    logger.error("Message handler error: %s", e)
        return True

    def _poll_loop(self) -> None:
        """Background polling loop for events."""
        while self._running:
            try:
                events = self.poll_events()
                for event in events:
                    self._dispatch(event)
            except Exception as e:  # noqa: BLE001
                logger.warning("Poll loop error: %s", e)
            time.sleep(self.poll_interval)

    def _beat(self, generation: int | None = None) -> None:
        """SSE connection heartbeat (POST /connection/beat, 2s liveness)."""
        try:
            body: dict[str, Any] = {"connection_id": self.connection_id}
            if generation is not None:
                body["generation"] = generation
            httpx.post(
                f"{self.switch_url}/agents/{self.agent_id}/connection/beat",
                json=body,
                headers=self._headers,
                timeout=5,
            )
        except (httpx.HTTPError, OSError) as e:
            logger.debug("Failed to unsubscribe before closing: %s", e)

    def _sse_loop(self) -> None:
        """SSE streaming loop: frames are `event: <type>` + `data: <AgentEvent>`."""
        headers = {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self.agent_api_key}",
        }
        params = {"connection_id": self.connection_id, "start_from": "head"}
        url = f"{self.switch_url}/agents/{self.agent_id}/events"
        generation: int | None = None
        last_beat = 0.0
        while self._running:
            try:
                with httpx.stream("GET", url, params=params, headers=headers, timeout=None) as resp:
                    if resp.status_code in (401, 403):
                        logger.error("Actual Switch SSE auth failed (%s)", resp.status_code)
                        return
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not self._running:
                            break
                        now = time.monotonic()
                        if now - last_beat > 2.0:
                            self._beat(generation)
                            last_beat = now
                        line = line.strip()
                        if line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        try:
                            raw = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            logger.debug("unparseable SSE line dropped")
                            continue
                        if isinstance(raw, dict) and raw.get("connection_id") and raw.get("generation"):
                            generation = raw.get("generation")
                            continue
                        self._dispatch(raw)
            except Exception as e:  # noqa: BLE001
                if not self._running:
                    break
                logger.warning("Actual Switch SSE disconnected: %s; reconnecting in 2s...", e)
                time.sleep(2.0)

