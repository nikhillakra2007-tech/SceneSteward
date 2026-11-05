"""Consent records — create, confirm, history. No unrestricted update exists:
corrections are new versions; confirmation is a one-way, human-only act."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession, OptionalUser, get_membership
from app.core import permissions
from app.core.database import system_context
from app.core.exceptions import NotFoundError, PermissionDenied, Unauthenticated
from app.core.security import decode_participant_token
from app.models import ConsentRecord, Participant
from app.schemas.common import Page
from app.schemas.consent import (
    ConsentConfirmRequest,
    ConsentRecordCreate,
    ConsentRecordOut,
)
from app.services import consent_service
from app.utils.pagination import PageParams, page_params

router = APIRouter(tags=["consent"])


def _out(record: ConsentRecord) -> ConsentRecordOut:
    return ConsentRecordOut.model_validate(record)


def _get_participant_scoped(db, participant_id: uuid.UUID, user: CurrentUser, roles: set[str] | None,
                            action: str) -> tuple[Participant, object]:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    is_self = participant.user_id is not None and participant.user_id == user.id
    if roles is not None and membership.role not in roles and not is_self:
        raise PermissionDenied(f"This role cannot perform that operation ({action})")
    return participant, membership


@router.post("/participants/{participant_id}/consent-records", response_model=ConsentRecordOut, status_code=201)
def create_consent_record(participant_id: uuid.UUID, payload: ConsentRecordCreate,
                          db: DbSession, user: CurrentUser) -> ConsentRecordOut:
    participant, _ = _get_participant_scoped(db, participant_id, user,
                                             permissions.PARTICIPANT_WRITE_ROLES, "record consent")
    if payload.source_document_id is not None:
        from app.models import ReleaseDocument
        doc = db.get(ReleaseDocument, payload.source_document_id)
        if doc is None or doc.participant_id != participant.id:
            raise NotFoundError("Source document not found")
    import uuid as _uuid
    correlation_id = _uuid.uuid4()
    record = consent_service.create_consent_record(
        db, participant=participant, project_id=participant.project_id,
        recorded_by_id=user.id, source_type=payload.source_type,
        source_document_id=payload.source_document_id,
        explanation=payload.explanation, choices=payload.choices,
        actor=("user", str(user.id)), correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(record)
    return _out(record)


@router.get("/participants/{participant_id}/consent-records", response_model=Page[ConsentRecordOut])
@router.get("/participants/{participant_id}/consents", response_model=Page[ConsentRecordOut])
def list_consent_records(
    participant_id: uuid.UUID,
    db: DbSession,
    user: OptionalUser,
    page: Annotated[PageParams, Depends(page_params)],
    token: str | None = None,
) -> Page[ConsentRecordOut]:
    if token:
        claims = decode_participant_token(token)
        if claims.get("sub") != str(participant_id):
            raise PermissionDenied("Access token does not match this participant")
        with system_context(db):
            participant = db.get(Participant, participant_id)
            if participant is None or str(participant.project_id) != claims.get("project_id"):
                raise NotFoundError("Participant not found")
            stmt = select(ConsentRecord).where(ConsentRecord.participant_id == participant.id)
            total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
            rows = db.execute(
                stmt.order_by(ConsentRecord.version_number.desc())
                .limit(page.limit).offset(page.offset)
            ).scalars().all()
            return Page(items=[_out(r) for r in rows], total=total, limit=page.limit, offset=page.offset)

    if user is None:
        raise Unauthenticated("Authentication or participant token required")

    participant, _membership = _get_participant_scoped(db, participant_id, user, None, "view consent")
    stmt = select(ConsentRecord).where(ConsentRecord.participant_id == participant.id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(ConsentRecord.version_number.desc())
                      .limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[_out(r) for r in rows], total=total, limit=page.limit, offset=page.offset)


def _get_record(db, record_id: uuid.UUID, user: CurrentUser):
    record = db.get(ConsentRecord, record_id)
    if record is None:
        raise NotFoundError("Consent record not found")
    get_membership(db, record.project_id, user)  # must be a project member
    return record


@router.get("/consent-records/{record_id}", response_model=ConsentRecordOut)
def get_consent_record(record_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ConsentRecordOut:
    return _out(_get_record(db, record_id, user))


@router.get("/consent-records/{record_id}/history", response_model=list[ConsentRecordOut])
def consent_record_history(record_id: uuid.UUID, db: DbSession, user: CurrentUser) -> list[ConsentRecordOut]:
    record = _get_record(db, record_id, user)
    rows = db.execute(
        select(ConsentRecord).where(ConsentRecord.participant_id == record.participant_id)
        .order_by(ConsentRecord.version_number.asc())
    ).scalars().all()
    return [_out(r) for r in rows]


@router.post("/consent-records/{record_id}/confirm", response_model=ConsentRecordOut)
def confirm_consent_record(record_id: uuid.UUID, payload: ConsentConfirmRequest,
                           db: DbSession, user: CurrentUser) -> ConsentRecordOut:
    record = db.get(ConsentRecord, record_id)
    if record is None:
        raise NotFoundError("Consent record not found")
    membership = get_membership(db, record.project_id, user)
    if membership.role not in permissions.CONSENT_CONFIRM_ROLES:
        raise PermissionDenied("Only owner, producer, or participant-care-lead may confirm consent")
    import uuid as _uuid
    correlation_id = _uuid.uuid4()
    updated = consent_service.confirm_consent_record(
        db, record=record, actor_user_id=user.id, actor=("user", str(user.id)),
        confirmation=payload.confirmation, evidence=payload.confirmation_evidence,
        expected_version=payload.expected_version, correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(updated)
    return _out(updated)
