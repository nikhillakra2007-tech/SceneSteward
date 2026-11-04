"""Switch integration interface.

SceneSteward's database is authoritative. Switch is a collaboration surface
only: it can carry structured context and findings, never decisions.

Supported connection modes (env SWITCH_ADAPTER):
  test — in-memory adapter, no network (development/tests)
  http — real adapter against SWITCH_BASE_URL using the agent protocol
         (SSE down, HTTP up, Bearer agent API key)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class SwitchStatus:
    status: str  # missing_credentials | configured_unverified | configured_verified | unavailable | failed_authentication | timeout
    detail: str | None = None


@dataclass
class SwitchMessage:
    room_id: str
    content: str
    correlation_id: str | None = None


@dataclass
class SwitchSendResult:
    ok: bool
    event_id: str | None = None
    error_code: str | None = None
    detail: str | None = None


class SwitchAdapter(Protocol):
    def verify_connection(self) -> SwitchStatus: ...
    def get_or_create_room(self, *, project_id: str, participant_id: str | None,
                            room_type: str, room_name: str, connection_id: str | None = None) -> dict[str, Any]: ...
    def send_review_context(self, *, room_id: str, summary: dict[str, Any], correlation_id: str) -> SwitchSendResult: ...
    def send_task_notification(self, *, room_id: str, task_title: str, correlation_id: str) -> SwitchSendResult: ...
    def validate_inbound_event(self, raw: dict[str, Any]) -> bool: ...
