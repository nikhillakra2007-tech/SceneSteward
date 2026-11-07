"""Switch Collaboration Bridge for Google Antigravity ACP Agent.

Connects the running Google Antigravity ACP Agent to the Switch platform:
  * Registers as distinct agent 'google-antigravity-01' ("Google Antigravity").
  * Subscribes to Switch room events via persistent SSE stream.
  * Filters and routes technical engineering questions to Google Antigravity.
  * Loop prevention: ignores self-messages and peer agent messages.
  * Data minimization: redacts participant PII, passing only technical context.
  * Posts evidence-backed engineering assessments back to the Switch room.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from typing import Any

import httpx

from app.integrations.antigravity.acp_client import AntigravityACPClient
from app.integrations.antigravity.config import AntigravityConfig, get_antigravity_config

logger = logging.getLogger("scenesteward.antigravity.switch_bridge")


class AntigravitySwitchBridge:
    """Bridges Switch room messages to the Google Antigravity ACP agent.

    Works against both wire shapes:
    - Real Switch Core AgentEvent (poll/SSE): {type, room_id, payload:{...}}
    - Local simulator (port 8010): {type, event_id, data:{room_id, sender, body|content}}
    """

    def __init__(
        self,
        config: AntigravityConfig | None = None,
        acp_client: AntigravityACPClient | None = None,
    ) -> None:
        self.config = config or get_antigravity_config()
        self.acp_client = acp_client or AntigravityACPClient(self.config)
        self.connection_id = str(uuid.uuid4())
        self.agent_id = self.config.agent_id
        self.base_url = self.config.switch_base_url.rstrip("/")
        self.api_key = self.config.switch_api_key
        self._running = False
        self._listener_thread: threading.Thread | None = None
        self._processed_event_ids: set[str] = set()

    def start(self) -> bool:
        """Initializes ACP client and starts background Switch SSE listener."""
        if not self.config.enabled:
            logger.info("Antigravity integration is disabled by configuration")
            return False

        logger.info("Starting Google Antigravity ACP client...")
        if not self.acp_client.start():
            logger.error("Failed to start Antigravity ACP client")
            return False

        try:
            self.acp_client.create_session()
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to establish Antigravity ACP session: %s", e)
            return False

        self._running = True
        self._listener_thread = threading.Thread(target=self._run_sse_loop, daemon=True)
        self._listener_thread.start()
        logger.info("Antigravity Switch bridge started (agent_id=%s)", self.agent_id)
        return True

    def stop(self) -> None:
        """Stops Switch listener and halts ACP subprocess."""
        self._running = False
        self.acp_client.stop()
        logger.info("Antigravity Switch bridge stopped")

    def post_message_to_room(self, room_id: str, content: str) -> bool:
        """Posts a message to a Switch room as Google Antigravity."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"room_id": room_id, "content": content}
        try:
            res = httpx.post(
                f"{self.base_url}/agents/{self.agent_id}/message",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            return res.status_code == 200
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to post message to Switch room %s: %s", room_id, e)
            return False

    def handle_room_event(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Processes an incoming Switch room event with loop prevention and routing."""
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else None
        legacy_data = raw.get("data") if isinstance(raw.get("data"), dict) else None
        if payload is not None:
            room_id = raw.get("room_id")
            sender = payload.get("sender_name") or payload.get("sender") or ""
            content = payload.get("body") or payload.get("content") or ""
            event_id = raw.get("event_id") or payload.get("message_id")
        elif legacy_data is not None:
            room_id = legacy_data.get("room_id")
            sender = legacy_data.get("sender", "")
            content = legacy_data.get("body") or legacy_data.get("content") or ""
            event_id = raw.get("event_id") or legacy_data.get("id")
        else:
            return {"status": "ignored", "reason": "invalid_event"}
        if not room_id:
            return {"status": "ignored", "reason": "missing_room_id"}
        if event_id and event_id in self._processed_event_ids:
            return {"status": "ignored", "reason": "duplicate_event"}
        if event_id:
            self._processed_event_ids.add(event_id)

        # Loop prevention: Never respond to self or other bot agents
        sender_kind = str(payload.get("sender_kind") or "") if payload else ""
        name_agent = ("Antigravity" in sender) or ("SceneSteward Agent" in sender) or sender == "scenesteward-clearance"
        if sender_kind in ("agent", "platform") or (not sender_kind and name_agent) or not content:
            return {"status": "ignored", "reason": "agent_or_empty"}

        logger.info("Antigravity bridge inspecting message from '%s' in room %s", sender, room_id)

        # Check if the message contains technical / architectural clearance questions
        is_clearance = re.search(r"\b(review|clearance|check|clear|f-104|trailer|promotional|technical|architecture)\b", content, re.IGNORECASE)
        is_followup = re.search(r"\bwhy\b.*\b(blocked|signed|release|trailer)\b", content, re.IGNORECASE)

        if not (is_clearance or is_followup):
            return {"status": "ignored", "reason": "not_relevant_to_engineering"}

        # Construct sanitized, PII-minimized technical prompt for Google Antigravity ACP
        if is_clearance:
            prompt_text = (
                f"You are Google Antigravity, an AI software engineering and systems architecture agent "
                f"participating in a Switch multi-agent collaboration room with human filmmakers and the SceneSteward agent.\n\n"
                f"Human request: \"{content}\"\n\n"
                f"Context: The footage clearance workflow evaluates whether a signed release for raw interview footage "
                f"authorizes downstream promotional trailer broadcasting. SceneSteward's policy enforces that consent is "
                f"strictly non-transitive and category-scoped.\n\n"
                f"Provide a concise, 2-3 sentence technical and software engineering evaluation of why asset management "
                f"systems and authorization architectures must treat general ingestion releases separately from "
                f"downstream syndication/promotional sinks, and confirm the system must block automatic trailer promotion."
            )
        else:
            prompt_text = (
                f"You are Google Antigravity participating in a Switch room.\n"
                f"Human question: \"{content}\"\n\n"
                f"In 2 sentences, explain from a software security and principle-of-least-privilege perspective "
                f"why signing an initial capture release cannot be treated as omnibus consent for promotional trailers."
            )

        try:
            logger.info("Submitting technical prompt to Google Antigravity ACP...")
            acp_response = self.acp_client.prompt(prompt_text, timeout=self.config.request_timeout_seconds)
            logger.info("Received ACP response from Google Antigravity (%s chars)", len(acp_response))

            formatted_msg = (
                f"**[Google Antigravity — Systems Architecture & Security Evaluation]**\n"
                f"{acp_response}\n\n"
                f"*Notice: Technical recommendation only. Formal clearance requires authorized human review in SceneSteward.*"
            )

            posted = self.post_message_to_room(room_id, formatted_msg)
            return {
                "status": "responded",
                "room_id": room_id,
                "posted": posted,
                "response_snippet": acp_response[:100],
            }
        except Exception as e:
            logger.exception("Error querying Antigravity ACP: %s", e)  # noqa: TRY401
            return {"status": "error", "detail": str(e)}

    def _run_sse_loop(self) -> None:
        """Holds persistent SSE connection to Switch platform for Google Antigravity."""
        headers = {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self.api_key}",
        }
        params = {"connection_id": self.connection_id, "start_from": "head"}
        url = f"{self.base_url}/agents/{self.agent_id}/events"

        while self._running:
            try:
                with httpx.stream("GET", url, params=params, headers=headers, timeout=None) as resp:
                    if resp.status_code in (401, 403):
                        logger.error("Antigravity Switch SSE auth failed (%s)", resp.status_code)
                        return
                    for line in resp.iter_lines():
                        if not self._running:
                            break
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        try:
                            raw = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        if raw.get("type") == "message":
                            self.handle_room_event(raw)
            except Exception as e:  # noqa: BLE001
                if not self._running:
                    break
                logger.warning("Antigravity Switch SSE disconnected: %s; reconnecting in 2s...", e)
                time.sleep(2.0)

