"""Reviews — list, read, record human decisions through a validated state machine."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession, get_membership
from app.core import permissions
from app.core.exceptions import NotFoundError, PermissionDenied
from app.models import Review
from app.schemas.common import Page
from app.schemas.reviews import (
    HumanDecisionRequest,
    RequestDiscussionRequest,
    ResolveRequest,
    ReviewOut,
)
from app.services import audit
from app.services import reviews as review_service
from app.utils.pagination import PageParams, page_params

router = APIRouter(tags=["reviews"])

logger = logging.getLogger(__name__)


def _out(r: Review) -> ReviewOut:
    return ReviewOut.model_validate(r)


@router.get("/projects/{project_id}/reviews", response_model=Page[ReviewOut])
def list_reviews(project_id: uuid.UUID, db: DbSession, user: CurrentUser,
                 page: Annotated[PageParams, Depends(page_params)],
                 review_status: str | None = None) -> Page[ReviewOut]:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view reviews")
    stmt = select(Review).where(Review.project_id == project_id)
    if review_status:
        stmt = stmt.where(Review.review_status == review_status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Review.created_at.desc())
                      .limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[_out(r) for r in rows], total=total, limit=page.limit, offset=page.offset)


def _get_review_scoped(db, review_id: uuid.UUID, user: CurrentUser, roles: set[str] | None, action: str):
    review = db.get(Review, review_id)
    if review is None:
        raise NotFoundError("Review not found")
    membership = get_membership(db, review.project_id, user)
    if roles is not None and membership.role not in roles:
        raise PermissionDenied(f"This role cannot perform that operation ({action})")
    return review, membership


@router.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(review_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ReviewOut:
    review, membership = _get_review_scoped(db, review_id, user, None, "view")
    if membership.role not in permissions.READ_ROLES:
        raise PermissionDenied("This role cannot view reviews")
    return _out(review)


@router.post("/reviews/{review_id}/human-decision", response_model=ReviewOut)
def human_decision(review_id: uuid.UUID, payload: HumanDecisionRequest,
                   db: DbSession, user: CurrentUser) -> ReviewOut:
    review, _ = _get_review_scoped(db, review_id, user, permissions.REVIEW_DECIDE_ROLES,
                                   "record a decision")
    use = review_service.record_human_decision(
        db, review=review, decision=payload.decision, reason=payload.reason,
        actor_user_id=user.id, expected_version=payload.expected_version,
    )
    import uuid as _uuid
    audit_evt = audit.record(db, project_id=review.project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="review.human_decision", entity_type="review", entity_id=review.id,
                 new_value={"decision": payload.decision,
                            "proposed_use_status": use.status if use else None},
                 reason=payload.reason,
                 correlation_id=_uuid.uuid4())
    db.commit()
    db.refresh(review)

    # If project is linked to a Switch room, notify the room with audit proof
    try:
        import hashlib

        from app.integrations.switch.agent_worker import SwitchAgentWorker
        from app.models import SwitchRoomLink
        link = db.query(SwitchRoomLink).filter(SwitchRoomLink.project_id == review.project_id).first()
        if link and link.switch_room_id:
            digest = hashlib.sha256(f"{audit_evt.id}:{review.id}:{payload.decision}:{payload.reason}".encode()).hexdigest()
            worker = SwitchAgentWorker()
            worker.notify_human_decision_committed(
                db,
                room_id=link.switch_room_id,
                review_id=str(review.id),
                decision=payload.decision,
                rationale=payload.reason,
                reviewer_name=user.full_name or "Authorized Reviewer",
                audit_event_id=str(audit_evt.id),
                hash_chain=digest,
            )
    except Exception:
        logger.exception("switch room notification failed after human decision")

    return _out(review)


@router.post("/reviews/{review_id}/request-participant-discussion", response_model=ReviewOut)
def request_participant_discussion(review_id: uuid.UUID, payload: RequestDiscussionRequest,
                                   db: DbSession, user: CurrentUser) -> ReviewOut:
    review, _ = _get_review_scoped(db, review_id, user, permissions.REVIEW_DECIDE_ROLES,
                                   "request a participant discussion")
    from app.core.exceptions import ConflictError, PreconditionFailed
    if review.version != payload.expected_version:
        raise ConflictError("Review was modified by another writer; reload and retry",
                            code="version_conflict")
    if review.review_status not in ("pending", "in_progress", "escalated"):
        raise PreconditionFailed("Discussion can only be requested for an open review",
                                 code="invalid_review_state")
    review.review_status = "in_progress"
    review.human_decision = "needs_participant_discussion"
    review.decision_reason = payload.reason
    review.decided_by = user.id
    review.decided_at = datetime.now(UTC)
    review.uncertainty = payload.reason
    review.version += 1

    from app.models import ProposedUse
    use = db.get(ProposedUse, review.proposed_use_id)
    if use is not None:
        use.status = "awaiting_participant_discussion"
        use.version += 1

    import uuid as _uuid
    corr = _uuid.uuid4()
    audit.record(db, project_id=review.project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="review.participant_discussion_requested", entity_type="review",
                 entity_id=review.id, reason=payload.reason, correlation_id=corr)
    from app.services import tasks
    tasks.create_task(
        db, project_id=review.project_id, participant_id=use.participant_id if use else None,
        task_type="participant_follow_up",
        title="Participant discussion requested",
        description=payload.reason,
        priority="high", source_type="review", source_id=review.id,
        created_by_actor_type="user",
    )
    db.commit()
    db.refresh(review)
    return _out(review)


@router.post("/reviews/{review_id}/resolve", response_model=ReviewOut)
def resolve_review(review_id: uuid.UUID, payload: ResolveRequest,
                   db: DbSession, user: CurrentUser) -> ReviewOut:
    review, _ = _get_review_scoped(db, review_id, user, permissions.REVIEW_RESOLVE_ROLES,
                                   "resolve a review")
    from app.core.exceptions import ConflictError, PreconditionFailed
    if review.version != payload.expected_version:
        raise ConflictError("Review was modified by another writer; reload and retry",
                            code="version_conflict")
    if review.review_status != "completed" or review.human_decision is None:
        raise PreconditionFailed("Only a completed review with a recorded decision can be resolved",
                                 code="review_not_decided")
    # Idempotent: resolving an already-resolved review returns it unchanged.
    import uuid as _uuid
    audit.record(db, project_id=review.project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="review.resolved", entity_type="review", entity_id=review.id,
                 reason=payload.note, correlation_id=_uuid.uuid4())
    db.commit()
    db.refresh(review)
    return _out(review)
