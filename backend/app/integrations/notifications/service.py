"""Notification sinks — how SceneSteward tells humans that something needs them.

MVP: notifications are materialised as human-owned tasks (type='integration_failure'
or 'review') plus structured logs. No email/SMS provider is wired; swapping in a
real provider means implementing NotificationSink and registering it in
get_notification_sink() — no call sites change.
"""
from __future__ import annotations

import logging
import uuid
from typing import Protocol

from sqlalchemy.orm import Session

from app.services import tasks

logger = logging.getLogger("scenesteward.notifications")


class NotificationSink(Protocol):
    def notify_integration_failure(
        self, db: Session, *, project_id: uuid.UUID, participant_id: uuid.UUID | None,
        title: str, detail: str, correlation_id: uuid.UUID | None,
    ) -> None: ...


class TaskNotificationSink:
    """Default sink: create a high-priority task for a human to triage."""

    def notify_integration_failure(
        self, db: Session, *, project_id: uuid.UUID, participant_id: uuid.UUID | None,
        title: str, detail: str, correlation_id: uuid.UUID | None,
    ) -> None:
        tasks.create_task(
            db, project_id=project_id, participant_id=participant_id,
            task_type="integration_failure", title=title, description=detail,
            priority="high", source_type="integration_event", source_id=None,
            created_by_actor_type="integration",
        )
        logger.warning("integration failure notification task created",
                       extra={"endpoint": "notifications.integration_failure",
                              "correlation_id": str(correlation_id) if correlation_id else None})


_default_sink = TaskNotificationSink()


def get_notification_sink() -> NotificationSink:
    return _default_sink


def notify_integration_failure(
    db: Session, *, project_id: uuid.UUID, participant_id: uuid.UUID | None,
    title: str, detail: str, correlation_id: uuid.UUID | None,
) -> None:
    sink = get_notification_sink()
    sink.notify_integration_failure(
        db, project_id=project_id, participant_id=participant_id,
        title=title, detail=detail, correlation_id=correlation_id,
    )
