"""Shared enumerations (enforced as CHECK constraints in the database).

Categories are intentionally plain text at the DB layer so they remain
extensible; the canonical list lives here and is validated at the API layer.
"""
from __future__ import annotations

ACCOUNT_STATUSES = ("active", "suspended", "deactivated", "pending")
PROJECT_STATUSES = ("active", "archived", "on_hold", "completed")
MEMBERSHIP_STATUSES = ("invited", "active", "suspended", "removed")
MEMBERSHIP_ROLES = (
    "project_owner", "producer", "director", "editor",
    "participant_care_lead", "viewer", "participant", "service_agent",
)
PARTICIPANT_STATUSES = ("active", "paused", "withdrawn")
CONTACT_TYPES = ("email", "phone", "postal", "other")

CONSENT_RECORD_STATUSES = ("draft", "awaiting_confirmation", "confirmed", "superseded", "revoked")
PARTICIPANT_CONFIRMATIONS = ("unconfirmed", "confirmed", "declined", "partial")
SOURCE_TYPES = ("interview", "document", "release_form", "verbal_recorded", "extracted", "imported", "manual")
CONSENT_CHOICES = ("agreed", "declined", "not_discussed", "needs_clarification", "explained", "awaiting_confirmation")

# Canonical consent categories (extensible — unknown categories are accepted but flagged).
CONSENT_CATEGORIES = (
    "interview_recording",
    "documentary_appearance",
    "name_identification",
    "face_identification",
    "sensitive_personal_details",
    "promotional_clips",
    "festival_submissions",
    "ai_transcription",
    "voice_cloning",
    "synthetic_likeness",
    "third_party_ai_processing",
    "new_audience",
    "new_territory",
    "new_platform",
    "new_story_context",
)

SIGNATURE_STATUSES = ("unknown", "unsigned", "signed", "partially_signed", "expired", "void")
EXTRACTION_STATUSES = ("pending", "processing", "extracted", "failed", "not_required")
SENSITIVITY_LEVELS = ("standard", "sensitive", "highly_sensitive")

PROPOSED_USE_STATUSES = (
    "draft", "submitted", "analysing", "analysis_complete",
    "awaiting_participant_discussion", "approved", "declined", "withdrawn", "superseded",
)
ANALYSIS_OUTCOMES = (
    "RECORDED_CHOICE_MATCH", "NEEDS_DISCUSSION", "PARTICIPANT_DECLINED",
    "HUMAN_REVIEW_REQUIRED", "UNRESOLVED",
)

REVIEWER_TYPES = ("human", "agent")
REVIEW_STATUSES = ("pending", "in_progress", "completed", "escalated", "cancelled")
HUMAN_DECISIONS = ("approve", "decline", "request_changes", "needs_participant_discussion", "escalate")

AGENT_NAMES = (
    "consent_analyst", "story_change_analyst", "participant_advocate",
    "ethics_reviewer", "production_coordinator",
)
AGENT_RUN_STATUSES = ("queued", "running", "succeeded", "failed", "timeout", "rejected")

COMMUNICATION_TYPES = ("email", "letter", "script", "call_notes", "sms", "other")
COMMUNICATION_STATUSES = ("draft", "awaiting_approval", "approved", "sent", "cancelled")

ACTOR_TYPES = ("user", "agent", "system", "integration")
INTEGRATION_PROCESSING_STATUSES = ("received", "processing", "processed", "failed", "dead_letter", "skipped_duplicate")

TASK_TYPES = ("review", "participant_follow_up", "unresolved_permission", "agent_review", "integration_failure", "general")
TASK_STATUSES = ("open", "in_progress", "blocked", "done", "cancelled")
TASK_PRIORITIES = ("low", "normal", "high", "urgent")

SWITCH_ROOM_TYPES = ("project", "participant_review")


def in_clause(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"
