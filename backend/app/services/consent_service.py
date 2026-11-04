"""Consent lifecycle: versioned records, explicit confirmation, supersession.

Invariants enforced here (and mirrored by database triggers):
  * Confirmed records are immutable — create a new version instead.
  * Only one version per participant is 'confirmed' at a time; older confirmed
    versions transition to 'superseded' when a new one is confirmed.
  * Missing categories are NOT agreement ('not_discussed' semantics live in the
    comparison engine).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import ConsentChoice, ConsentRecord, Participant
from app.schemas.consent import ConsentChoiceIn
from app.services import audit


def next_version_number(db: Session, participant_id: uuid.UUID) -> int:
    current = db.execute(
        select(func.max(ConsentRecord.version_number)).where(ConsentRecord.participant_id == participant_id)
    ).scalar()
    return (current or 0) + 1


def lock_participant(db: Session, participant_id: uuid.UUID) -> Participant:
    stmt = select(Participant).where(Participant.id == participant_id).with_for_update()
    participant = db.execute(stmt).scalar_one()
    return participant


def create_consent_record(
    db: Session,
    *,
    participant: Participant,
    project_id: uuid.UUID,
    recorded_by_id: uuid.UUID,
    source_type: str,
    source_document_id: uuid.UUID | None,
    explanation: str | None,
    choices: list[ConsentChoiceIn],
    actor: tuple[str, str],
    correlation_id: uuid.UUID,
    initial_status: str = "awaiting_confirmation",
    unconfirmed_choices: bool = True,
) -> ConsentRecord:
    lock_participant(db, participant.id)
    version = next_version_number(db, participant.id)
    record = ConsentRecord(
        participant_id=participant.id,
        project_id=project_id,
        version_number=version,
        record_status=initial_status,
        source_type=source_type,
        source_document_id=source_document_id,
        explanation=explanation,
        recorded_by=recorded_by_id,
        participant_confirmation="unconfirmed",
    )
    for c in choices:
        record.choices.append(ConsentChoice(
            category=c.category,
            choice=c.choice,
            explanation=c.explanation,
            evidence_reference=c.evidence_reference,
            source_type=c.source_type,
            confidence_if_extracted=c.confidence_if_extracted,
        ))
    db.add(record)
    db.flush()
    audit.record(
        db, project_id=project_id, participant_id=participant.id,
        actor_type=actor[0], actor_id=actor[1],
        action="consent_record.created",
        entity_type="consent_record", entity_id=record.id,
        new_value={"version_number": version, "source_type": source_type,
                   "record_status": record.record_status,
                   "categories": [c.category for c in choices]},
        correlation_id=correlation_id,
    )
    return record


def get_latest_confirmed(db: Session, participant_id: uuid.UUID) -> ConsentRecord | None:
    stmt = (
        select(ConsentRecord)
        .where(
            ConsentRecord.participant_id == participant_id,
            ConsentRecord.record_status == "confirmed",
            ConsentRecord.participant_confirmation == "confirmed",
        )
        .order_by(ConsentRecord.version_number.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_confirmed_history(db: Session, participant_id: uuid.UUID) -> list[ConsentRecord]:
    stmt = (
        select(ConsentRecord)
        .where(
            ConsentRecord.participant_id == participant_id,
            ConsentRecord.record_status.in_(("confirmed", "superseded")),
            ConsentRecord.participant_confirmation == "confirmed",
        )
        .order_by(ConsentRecord.version_number.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_record_for_participant(db: Session, record_id: uuid.UUID, participant_id: uuid.UUID) -> ConsentRecord:
    record = db.get(ConsentRecord, record_id)
    if record is None or record.participant_id != participant_id:
        raise NotFoundError("Consent record not found")
    return record


def confirm_consent_record(
    db: Session,
    *,
    record: ConsentRecord,
    actor_user_id: uuid.UUID,
    actor: tuple[str, str],
    confirmation: str,          # 'confirmed' | 'declined' | 'partial'
    evidence: str,
    expected_version: int,
    correlation_id: uuid.UUID,
) -> ConsentRecord:
    if record.version != expected_version:
        raise ConflictError("Consent record was modified by another writer; reload and retry",
                            code="version_conflict")
    if record.participant_confirmation == "confirmed" and record.record_status == "confirmed":
        raise ConflictError("Consent record is already confirmed; create a new version to change it",
                            code="already_confirmed")

    now = datetime.now(UTC)
    previous_status = record.record_status
    record.participant_confirmation = confirmation
    if confirmation == "confirmed":
        record.record_status = "confirmed"
        record.confirmed_at = now
        # Supersede any other confirmed version for this participant.
        others = db.execute(
            select(ConsentRecord).where(
                ConsentRecord.participant_id == record.participant_id,
                ConsentRecord.id != record.id,
                ConsentRecord.record_status == "confirmed",
                ConsentRecord.participant_confirmation == "confirmed",
            )
        ).scalars().all()
        for other in others:
            other.record_status = "superseded"
            audit.record(
                db, project_id=other.project_id, participant_id=other.participant_id,
                actor_type=actor[0], actor_id=actor[1],
                action="consent_record.superseded",
                entity_type="consent_record", entity_id=other.id,
                previous_value={"record_status": "confirmed"},
                new_value={"record_status": "superseded", "superseded_by_record_id": str(record.id)},
                correlation_id=correlation_id,
            )
        for choice in record.choices:
            choice.confirmed_by = actor_user_id
            choice.confirmed_at = now
    elif confirmation == "declined":
        record.record_status = "revoked"
        record.confirmed_at = None
    else:  # partial — not usable yet
        record.record_status = "awaiting_confirmation"
        record.confirmed_at = None
    record.version += 1

    audit.record(
        db, project_id=record.project_id, participant_id=record.participant_id,
        actor_type=actor[0], actor_id=actor[1],
        action=f"consent_record.{confirmation}",
        entity_type="consent_record", entity_id=record.id,
        previous_value={"record_status": previous_status, "participant_confirmation": "unconfirmed"},
        new_value={"record_status": record.record_status, "participant_confirmation": confirmation,
                   "confirmation_evidence": evidence},
        reason=evidence,
        correlation_id=correlation_id,
    )
    return record
