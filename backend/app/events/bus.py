"""Lightweight event bus — in-process pub/sub with failure isolation.

Events are ancillary: publishing never mutates core state and a failing
subscriber never breaks the caller. Used today for observability hooks;
Switch/notifications subscribe here as they come online.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

logger = logging.getLogger("scenesteward.events")

TOPICS = {
    "proposed_use.analysed",
    "switch.delivery_failed",
    "switch.delivery_succeeded",
    "document.extraction_failed",
    "document.extracted",
    "agent_run.completed",
    "review.human_decision",
    "participant.clarification_requested",
    "participant.withdrawal_requested",
    "consent.updated",
}


@dataclass(frozen=True)
class Event:
    topic: str
    payload: dict[str, Any]
    correlation_id: UUID | None = None


Handler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = {}

    def subscribe(self, topic: str, handler: Handler) -> None:
        if topic not in TOPICS:
            raise ValueError(f"unknown topic: {topic}")
        self._subscribers.setdefault(topic, []).append(handler)

    def publish(self, topic: str, *, correlation_id: UUID | None = None, **payload: Any) -> Event:
        event = Event(topic=topic, payload=payload, correlation_id=correlation_id)
        for handler in self._subscribers.get(topic, []):
            try:
                handler(event)
            except Exception:
                logger.exception("event subscriber failed topic=%s", topic)
        return event


bus = EventBus()

# Default subscriber: structured log line per event (for log collectors/alerting).
bus.subscribe("proposed_use.analysed", lambda e: logger.info(
    "event", extra={"endpoint": e.topic, "correlation_id": str(e.correlation_id) if e.correlation_id else None}))
bus.subscribe("switch.delivery_failed", lambda e: logger.warning(
    "event", extra={"endpoint": e.topic, "correlation_id": str(e.correlation_id) if e.correlation_id else None}))
bus.subscribe("document.extraction_failed", lambda e: logger.warning(
    "event", extra={"endpoint": e.topic, "correlation_id": str(e.correlation_id) if e.correlation_id else None}))


def publish(topic: str, *, correlation_id: UUID | None = None, **payload: Any) -> Event:
    return bus.publish(topic, correlation_id=correlation_id, **payload)
