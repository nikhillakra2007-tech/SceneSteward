"""In-memory Switch adapter for development and tests.

Deterministic, no network. Live connectivity is NOT exercised by this adapter;
tests using it are labelled 'mock' in TESTING.md.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.integrations.switch.base import SwitchMessage, SwitchSendResult, SwitchStatus


class InMemorySwitchAdapter:
    name = "test"

    def __init__(self) -> None:
        self.rooms: dict[str, dict[str, Any]] = {}
        self.sent: list[SwitchMessage] = []
        self._fail_next: set[str] = set()

    # test hooks -------------------------------------------------------------
    def fail_next(self, method: str) -> None:
        self._fail_next.add(method)

    def _raise_if_armed(self, method: str) -> None:
        if method in self._fail_next:
            self._fail_next.discard(method)
            raise RuntimeError(f"injected failure for {method}")

    # adapter interface --------------------------------------------------------
    def verify_connection(self) -> SwitchStatus:
        return SwitchStatus(status="configured_verified", detail="test adapter — no network traffic was performed")

    def get_or_create_room(self, *, project_id: str, participant_id: str | None,
                            room_type: str, room_name: str, connection_id: str | None = None) -> dict[str, Any]:
        self._raise_if_armed("get_or_create_room")
        key = f"{project_id}:{participant_id or '-'}:{room_type}"
        for room_id, room in self.rooms.items():
            if room["key"] == key:
                return {**room, "reused": True}
        room_id = f"switch-room-{uuid.uuid4().hex[:12]}"
        room = {"key": key, "room_id": room_id, "name": room_name, "room_type": room_type}
        self.rooms[room_id] = room
        return {**room, "reused": False}

    def send_review_context(self, *, room_id: str, summary: dict[str, Any], correlation_id: str) -> SwitchSendResult:
        self._raise_if_armed("send_review_context")
        if room_id not in self.rooms:
            return SwitchSendResult(ok=False, error_code="room_not_found", detail="Room is not linked in this adapter")
        self.sent.append(SwitchMessage(room_id=room_id, content=str(summary), correlation_id=correlation_id))
        return SwitchSendResult(ok=True, event_id=f"evt-{uuid.uuid4().hex[:12]}")

    def send_task_notification(self, *, room_id: str, task_title: str, correlation_id: str) -> SwitchSendResult:
        self._raise_if_armed("send_task_notification")
        if room_id not in self.rooms:
            return SwitchSendResult(ok=False, error_code="room_not_found")
        self.sent.append(SwitchMessage(room_id=room_id, content=f"Task: {task_title}", correlation_id=correlation_id))
        return SwitchSendResult(ok=True, event_id=f"evt-{uuid.uuid4().hex[:12]}")

    def validate_inbound_event(self, raw: dict[str, Any]) -> bool:
        if not isinstance(raw, dict):
            return False
        return bool(raw.get("type")) and ("sequence" in raw or "event_id" in raw or raw.get("type") == "message")
