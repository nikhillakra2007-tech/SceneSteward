"""Notification fan-out for human-actionable alerts (tasks + logs today; providers later)."""
from app.integrations.notifications.service import (
    NotificationSink,
    TaskNotificationSink,
    get_notification_sink,
    notify_integration_failure,
)

__all__ = [
    "NotificationSink",
    "TaskNotificationSink",
    "get_notification_sink",
    "notify_integration_failure",
]
