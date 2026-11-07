"""HTTP adapter for the real Switch (Agent Switch) agent protocol.

Wire format (verified against the Switch source at C:\\...\\SWITCH\\switch):
  * Register (once):  POST /agents/register-known  (Bearer REGISTRATION token)
  * Auth (all calls): Authorization: Bearer <agent API key>
  * Health:           GET  /health
  * Ops discovery:    GET  /agents/{id}/ops
  * Ops call:         POST /agents/{id}/ops/{operation}   (arguments unwrapped;
                      requires X-Switch-Connection-Id of an OPEN connection)
  * Post message:     POST /agents/{id}/message           {room_id, content}
  * Events:           GET  /agents/{id}/events            (SSE)
There is NO outbound webhook mechanism for external services; incoming events
are only visible by holding the agent SSE connection.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import UpstreamUnavailable
from app.integrations.switch.base import SwitchSendResult, SwitchStatus

logger = logging.getLogger("scenesteward.switch")


class SwitchNotConnected(UpstreamUnavailable):
    pass


class HttpSwitchAdapter:
    name = "http"

    def __init__(self) -> None:
        s = get_settings()
        if not (s.switch_base_url and s.switch_api_key and s.switch_agent_id):
            raise UpstreamUnavailable(
                "SWITCH_ADAPTER=http requires SWITCH_BASE_URL, SWITCH_API_KEY and SWITCH_AGENT_ID",
                code="switch_unconfigured",
            )
        self.base = s.switch_base_url.rstrip("/")
        self.agent_id = s.switch_agent_id
        self._client = httpx.Client(
            base_url=self.base,
            headers={"Authorization": f"Bearer {s.switch_api_key}"},
            timeout=httpx.Timeout(10.0, connect=5.0),
        )

    # -- diagnostics ---------------------------------------------------------
    def verify_connection(self) -> SwitchStatus:
        try:
            health = self._client.get("/health")
        except httpx.TimeoutException:
            return SwitchStatus(status="timeout", detail="health check timed out")
        except httpx.HTTPError:
            return SwitchStatus(status="unavailable", detail="health check failed")
        if health.status_code != 200:
            return SwitchStatus(status="unavailable", detail=f"health returned {health.status_code}")
        try:
            ops = self._client.get(f"/agents/{self.agent_id}/ops")
        except httpx.TimeoutException:
            return SwitchStatus(status="timeout", detail="ops discovery timed out")
        except httpx.HTTPError:
            return SwitchStatus(status="unavailable", detail="ops discovery failed")
        if ops.status_code in (401, 403):
            return SwitchStatus(status="failed_authentication", detail="agent API key rejected")
        if ops.status_code == 404:
            return SwitchStatus(status="failed_authentication", detail="agent id not found")
        if ops.status_code != 200:
            return SwitchStatus(status="unavailable", detail=f"ops discovery returned {ops.status_code}")
        return SwitchStatus(status="configured_verified", detail="health + authenticated ops discovery succeeded")

    # -- rooms -----------------------------------------------------------------
    def get_or_create_room(self, *, project_id: str, participant_id: str | None,
                            room_type: str, room_name: str,
                            connection_id: str | None = None) -> dict[str, Any]:
        if not connection_id:
            raise SwitchNotConnected(
                "Creating a room requires an open agent connection (X-Switch-Connection-Id). "
                "Run scripts/switch_listener.py to hold one, or pass an existing connection_id.",
                code="switch_not_connected",
            )
        resp = self._client.post(
            f"/agents/{self.agent_id}/ops/create_room",
            headers={"X-Switch-Connection-Id": connection_id},
            json={"name": room_name, "visibility": "private"},
        )
        if resp.status_code in (401, 403):
            raise UpstreamUnavailable("Switch rejected the agent API key", code="switch_failed_authentication")
        if resp.status_code == 429:
            raise UpstreamUnavailable("Switch rate limit during room creation", code="switch_rate_limited")
        if resp.status_code >= 400:
            logger.warning("create_room failed status=%s", resp.status_code)
            raise UpstreamUnavailable("Switch room creation failed", code="switch_room_failed")
        data = resp.json().get("result", {})
        room_id = data.get("room_id") or data.get("id")
        return {"room_id": room_id, "name": room_name, "room_type": room_type, "reused": False}

    # -- messaging -------------------------------------------------------------
    def send_review_context(self, *, room_id: str, summary: dict[str, Any], correlation_id: str) -> SwitchSendResult:
        content = (
            "SceneSteward review context (structured, correlation " + correlation_id + "):\n"
            f"- proposed_use_id: {summary.get('proposed_use_id')}\n"
            f"- outcome: {summary.get('outcome')}\n"
            f"- missing_categories: {', '.join(summary.get('missing_categories', [])) or 'none'}\n"
            f"- declined_categories: {', '.join(summary.get('declined_categories', [])) or 'none'}\n"
            "Formal decisions must be recorded in SceneSteward by an authorised human; chat is not consent."
        )
        return self._post_message(room_id, content, correlation_id)

    def send_task_notification(self, *, room_id: str, task_title: str, correlation_id: str) -> SwitchSendResult:
        return self._post_message(room_id, f"SceneSteward task (correlation {correlation_id}): {task_title}", correlation_id)

    def _post_message(self, room_id: str, content: str, correlation_id: str) -> SwitchSendResult:
        try:
            resp = self._client.post(f"/agents/{self.agent_id}/message",
                                     json={"room_id": room_id, "content": content})
        except httpx.TimeoutException:
            return SwitchSendResult(ok=False, error_code="timeout")
        except httpx.HTTPError:
            return SwitchSendResult(ok=False, error_code="unavailable")
        if resp.status_code == 429:
            return SwitchSendResult(ok=False, error_code="rate_limited", detail=resp.headers.get("retry-after"))
        if resp.status_code == 422:
            return SwitchSendResult(ok=False, error_code="guardrail_blocked")
        if resp.status_code in (401, 403):
            return SwitchSendResult(ok=False, error_code="failed_authentication")
        if resp.status_code >= 400:
            logger.warning("switch message failed status=%s", resp.status_code)
            return SwitchSendResult(ok=False, error_code=f"http_{resp.status_code}")
        return SwitchSendResult(ok=True, event_id=str(resp.json().get("event_id")))

    # -- inbound -----------------------------------------------------------------
    def validate_inbound_event(self, raw: dict[str, Any]) -> bool:
        if not isinstance(raw, dict):
            return False
        if not raw.get("type"):
            return False
        # Domain events must carry a sequence; control frames are always accepted by type.
        if raw["type"] in {"connection_state", "gap", "evicted", "subscription_changed"}:
            return True
        # Legacy simulator: sequence / event_id at top level
        if isinstance(raw.get("sequence"), int) or raw.get("event_id"):
            return True
        # Real Switch Core AgentEvent (poll): {type, room_id, payload:{message_id, body, ...}}
        # Real SSE frame data: same AgentEvent plus optional sequence/position/missed.
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else None
        if isinstance(raw.get("room_id"), str) and isinstance(payload, dict):
            if payload.get("body") is not None or payload.get("message_id"):
                return True
            return True  # still a well-formed AgentEvent shell (room_join/command)
        # Legacy simulator data-nested shape
        data = raw.get("data") if isinstance(raw.get("data"), dict) else None
        return data is not None
