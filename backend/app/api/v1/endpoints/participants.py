"""Participants — roster, profiles, protected contact records, consent history."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import (
    CurrentUser,
    DbSession,
    get_membership,
    get_project,
)
from app.core import permissions
from app.core.exceptions import ConflictError, NotFoundError, PermissionDenied
from app.core.security import decrypt_secret, encrypt_secret
from app.models import ConsentRecord, Participant, ParticipantContactRecord, User
from app.schemas.common import Page
from app.schemas.participants import (
    ConsentHistoryEntry,
    ContactRecordCreate,
    ContactRecordOut,
    ParticipantCreate,
    ParticipantOut,
    ParticipantUpdate,
)
from app.services import audit
from app.utils.pagination import PageParams, page_params

router = APIRouter(tags=["participants"])


def _require_roles(membership, roles, what: str) -> None:
    if membership.role not in roles:
        raise PermissionDenied(f"This role cannot perform that operation ({what})")


def _can_read_contacts(role: str) -> bool:
    return role in permissions.SENSITIVE_READ_ROLES


@router.post("/projects/{project_id}/participants", response_model=ParticipantOut, status_code=201)
def create_participant(project_id: uuid.UUID, payload: ParticipantCreate,
                       db: DbSession, user: CurrentUser) -> ParticipantOut:
    membership = get_membership(db, project_id, user)
    _require_roles(membership, permissions.PARTICIPANT_WRITE_ROLES, "create participant")
    get_project(db, project_id)
    if payload.linked_user_id is not None:
        linked = db.get(User, payload.linked_user_id)
        if linked is None:
            raise NotFoundError("Linked user not found")
    participant = Participant(
        project_id=project_id,
        user_id=payload.linked_user_id,
        display_name=payload.display_name.strip(),
        preferred_language=payload.preferred_language,
        preferred_contact_method=payload.preferred_contact_method,
        accessibility_requirements=payload.accessibility_requirements,
        privacy_preferences=payload.privacy_preferences,
    )
    db.add(participant)
    db.flush()
    audit.record(db, project_id=project_id, participant_id=participant.id,
                 actor_type="user", actor_id=str(user.id),
                 action="participant.created", entity_type="participant", entity_id=participant.id,
                 new_value={"display_name": participant.display_name})
    db.commit()
    db.refresh(participant)
    return ParticipantOut.model_validate(participant)


@router.get("/projects/{project_id}/participants", response_model=Page[ParticipantOut])
def list_participants(project_id: uuid.UUID, db: DbSession, user: CurrentUser,
                      page: Annotated[PageParams, Depends(page_params)]) -> Page[ParticipantOut]:
    membership = get_membership(db, project_id, user)
    stmt = select(Participant).where(Participant.project_id == project_id)
    if membership.role == permissions.PARTICIPANT:
        # Linked participants see only their own record.
        stmt = stmt.where(Participant.user_id == user.id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Participant.created_at.asc()).limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[ParticipantOut.model_validate(p) for p in rows],
                total=total, limit=page.limit, offset=page.offset)


def _get_visible_participant(db, participant_id: uuid.UUID, user: CurrentUser) -> Participant:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    if membership.role == permissions.PARTICIPANT and participant.user_id != user.id:
        raise NotFoundError("Participant not found")
    return participant


@router.get("/participants/{participant_id}", response_model=ParticipantOut)
def get_participant(participant_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ParticipantOut:
    return ParticipantOut.model_validate(_get_visible_participant(db, participant_id, user))


@router.patch("/participants/{participant_id}", response_model=ParticipantOut)
def update_participant(participant_id: uuid.UUID, payload: ParticipantUpdate,
                       db: DbSession, user: CurrentUser) -> ParticipantOut:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    is_self = participant.user_id is not None and participant.user_id == user.id
    if is_self and membership.role == permissions.PARTICIPANT:
        # Linked participants may update ONLY communication/accessibility preferences.
        for field in ("preferred_language", "preferred_contact_method", "accessibility_requirements"):
            value = getattr(payload, field)
            if value is not None:
                setattr(participant, field, value)
        participant.updated_at = datetime.now(UTC)
        audit.record(db, project_id=participant.project_id, participant_id=participant.id,
                     actor_type="user", actor_id=str(user.id),
                     action="participant.self_updated", entity_type="participant",
                     entity_id=participant.id)
        db.commit()
        db.refresh(participant)
        return ParticipantOut.model_validate(participant)
    _require_roles(membership, permissions.PARTICIPANT_WRITE_ROLES, "edit participant")
    if participant.version != payload.expected_version:
        raise ConflictError("Participant was modified by another writer; reload and retry",
                            code="version_conflict")
    previous = {"display_name": participant.display_name, "participant_status": participant.participant_status}
    for field in ("display_name", "preferred_language", "preferred_contact_method",
                  "accessibility_requirements", "privacy_preferences", "participant_status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(participant, field, value)
    participant.version += 1
    participant.updated_at = datetime.now(UTC)
    audit.record(db, project_id=participant.project_id, participant_id=participant.id,
                 actor_type="user", actor_id=str(user.id),
                 action="participant.updated", entity_type="participant", entity_id=participant.id,
                 previous_value=previous,
                 new_value={"display_name": participant.display_name,
                            "participant_status": participant.participant_status})
    db.commit()
    db.refresh(participant)
    return ParticipantOut.model_validate(participant)


@router.get("/participants/{participant_id}/history", response_model=list[ConsentHistoryEntry])
def participant_history(participant_id: uuid.UUID, db: DbSession, user: CurrentUser) -> list[ConsentHistoryEntry]:
    participant = _get_visible_participant(db, participant_id, user)
    rows = db.execute(
        select(ConsentRecord).where(ConsentRecord.participant_id == participant.id)
        .order_by(ConsentRecord.version_number.desc())
    ).scalars().all()
    return [ConsentHistoryEntry(
        record_id=r.id, version_number=r.version_number, record_status=r.record_status,
        participant_confirmation=r.participant_confirmation, source_type=r.source_type,
        confirmed_at=r.confirmed_at, created_at=r.created_at, choice_count=len(r.choices),
    ) for r in rows]


# --- protected contact records --------------------------------------------------

@router.get("/participants/{participant_id}/contacts", response_model=list[ContactRecordOut])
def list_contacts(participant_id: uuid.UUID, db: DbSession, user: CurrentUser) -> list[ContactRecordOut]:
    participant = _get_visible_participant(db, participant_id, user)
    membership = get_membership(db, participant.project_id, user)
    is_self = participant.user_id is not None and participant.user_id == user.id
    if not is_self and not _can_read_contacts(membership.role):
        raise PermissionDenied("Contact details require owner, producer, or participant-care-lead access")
    rows = db.execute(
        select(ParticipantContactRecord).where(ParticipantContactRecord.participant_id == participant.id)
        .order_by(ParticipantContactRecord.created_at.asc())
    ).scalars().all()
    if rows:
        audit.record(
            db,
            project_id=participant.project_id,
            participant_id=participant.id,
            actor_type="user",
            actor_id=str(user.id),
            action="participant_contact.read",
            entity_type="participant",
            entity_id=participant.id,
            new_value={"contact_count": len(rows)},
        )
        db.commit()
    return [ContactRecordOut(
        id=r.id, participant_id=r.participant_id, contact_type=r.contact_type,
        value=decrypt_secret(r.encrypted_contact_data), verified_at=r.verified_at,
        created_at=r.created_at, updated_at=r.updated_at,
    ) for r in rows]


@router.post("/participants/{participant_id}/contacts", response_model=ContactRecordOut, status_code=201)
def add_contact(participant_id: uuid.UUID, payload: ContactRecordCreate,
                db: DbSession, user: CurrentUser) -> ContactRecordOut:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    _require_roles(membership, permissions.PARTICIPANT_WRITE_ROLES, "add contact")
    record = ParticipantContactRecord(
        participant_id=participant.id,
        contact_type=payload.contact_type,
        encrypted_contact_data=encrypt_secret(payload.value),
    )
    db.add(record)
    db.flush()
    audit.record(db, project_id=participant.project_id, participant_id=participant.id,
                 actor_type="user", actor_id=str(user.id),
                 action="contact.created", entity_type="participant_contact_record",
                 entity_id=record.id, new_value={"contact_type": record.contact_type})
    db.commit()
    db.refresh(record)
    return ContactRecordOut(
        id=record.id, participant_id=record.participant_id, contact_type=record.contact_type,
        value=payload.value, verified_at=record.verified_at,
        created_at=record.created_at, updated_at=record.updated_at,
    )
