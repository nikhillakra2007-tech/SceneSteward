"""Review state machine — validated transitions for the human-decision endpoints."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PreconditionFailed
from app.models import ProposedUse, Review

# Allowed transitions per review_status (enforced server-side, never by role hints alone).
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "completed", "cancelled"},
    "in_progress": {"completed", "escalated", "cancelled"},
    "completed": set(),
    "escalated": {"in_progress", "completed", "cancelled"},
    "cancelled": set(),
}

DECISION_TO_PROPOSED_USE_STATUS = {
    "approve": "approved",
    "decline": "declined",
    "request_changes": "analysis_complete",
    "needs_participant_discussion": "awaiting_participant_discussion",
    "escalate": "analysis_complete",
}


def get_review(db: Session, review_id: uuid.UUID) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise NotFoundError("Review not found")
    return review


def _check_version(review: Review, expected_version: int) -> None:
    if review.version != expected_version:
        raise ConflictError("Review was modified by another writer; reload and retry", code="version_conflict")


def _transition(review: Review, target: str) -> None:
    allowed = VALID_TRANSITIONS.get(review.review_status, set())
    if target not in allowed:
        raise PreconditionFailed(
            f"Cannot move review from {review.review_status!r} to {target!r}",
            code="invalid_review_transition",
        )
    review.review_status = target


def record_human_decision(db: Session, *, review: Review, decision: str, reason: str,
                          actor_user_id: uuid.UUID, expected_version: int) -> ProposedUse:
    _check_version(review, expected_version)
    if review.review_status in ("completed", "cancelled"):
        raise ConflictError("Review is already finalised; decisions are immutable", code="already_finalised")
    if review.review_status == "pending":
        review.review_status = "in_progress"
    _transition(review, "completed")
    now = datetime.now(UTC)
    review.human_decision = decision
    review.decision_reason = reason
    review.decided_by = actor_user_id
    review.decided_at = now
    review.completed_at = now
    review.version += 1

    use = db.get(ProposedUse, review.proposed_use_id)
    if use is not None:
        use.status = DECISION_TO_PROPOSED_USE_STATUS[decision]
        use.version += 1
    return use  # type: ignore[return-value]
