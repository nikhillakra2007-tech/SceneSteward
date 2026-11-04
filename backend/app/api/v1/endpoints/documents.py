"""Release documents — signed upload/download URLs, private storage, extraction."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import (
    CurrentUser,
    DbSession,
    get_membership,
    get_project_participant,  # noqa: F401  (kept for future scoping)
)
from app.core import permissions
from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDenied,
    PreconditionFailed,
)
from app.integrations.storage import get_storage_provider
from app.models import Participant, ReleaseDocument
from app.schemas.common import Page
from app.schemas.documents import (
    ALLOWED_EXTENSIONS,
    ALLOWED_UPLOAD_MIMES,
    CompleteUploadRequest,
    DocumentOut,
    DownloadUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services import audit
from app.utils.pagination import PageParams, page_params

router = APIRouter(tags=["documents"])
settings = get_settings()

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


def _safe_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1].strip()
    cleaned = _SAFE_NAME.sub("_", base)[:120] or "document"
    return cleaned


def _doc_out(d: ReleaseDocument) -> DocumentOut:
    return DocumentOut.model_validate(d)


def _doc_access(db, document: ReleaseDocument, user) -> str:
    membership = get_membership(db, document.project_id, user)
    participant = db.get(Participant, document.participant_id)
    is_self = bool(participant and participant.user_id == user.id)
    if not is_self and membership.role not in permissions.SENSITIVE_READ_ROLES:
        raise PermissionDenied("Documents are visible to owner, producer, participant-care-lead, or the participant")
    return membership.role


@router.post("/participants/{participant_id}/documents/upload-url",
             response_model=UploadUrlResponse, status_code=201)
def request_upload_url(participant_id: uuid.UUID, payload: UploadUrlRequest,
                       db: DbSession, user: CurrentUser) -> UploadUrlResponse:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    if membership.role not in permissions.PARTICIPANT_WRITE_ROLES:
        raise PermissionDenied("This role cannot upload release documents")
    max_bytes = settings.max_upload_bytes
    if payload.file_size > max_bytes:
        raise PreconditionFailed(f"File exceeds the {max_bytes}-byte limit", code="file_too_large")
    safe = _safe_filename(payload.original_filename)
    ext = Path(safe).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise PreconditionFailed(f"Extension {ext!r} is not allowed", code="extension_not_allowed")
    storage_key = f"{participant.project_id}/{participant.id}/{uuid.uuid4().hex}_{safe}"
    provider = get_storage_provider()
    url = provider.create_upload_target(storage_key, max_bytes=max_bytes,
                                        ttl_seconds=settings.signed_url_ttl_seconds)
    audit.record(db, project_id=participant.project_id, participant_id=participant.id,
                 actor_type="user", actor_id=str(user.id),
                 action="document.upload_url_issued", entity_type="release_document", entity_id=None,
                 new_value={"filename": safe, "mime_type": payload.mime_type, "file_size": payload.file_size})
    db.commit()
    return UploadUrlResponse(storage_key=storage_key, upload_url=url,
                             expires_in_seconds=settings.signed_url_ttl_seconds,
                             max_upload_bytes=max_bytes)


@router.post("/participants/{participant_id}/documents/complete-upload",
             response_model=DocumentOut, status_code=201)
def complete_upload(participant_id: uuid.UUID, payload: CompleteUploadRequest,
                    db: DbSession, user: CurrentUser) -> DocumentOut:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    if membership.role not in permissions.PARTICIPANT_WRITE_ROLES:
        raise PermissionDenied("This role cannot finalise uploads")
    if not payload.storage_key.startswith(f"{participant.project_id}/{participant.id}/"):
        raise PreconditionFailed("Storage key does not belong to this participant/project", code="key_mismatch")

    provider = get_storage_provider()
    if not provider.exists(payload.storage_key):
        raise PreconditionFailed("No file found at that storage key — upload first", code="upload_missing")
    size = provider.size(payload.storage_key)
    if size <= 0 or size > settings.max_upload_bytes:
        provider.delete(payload.storage_key)
        raise PreconditionFailed("Stored file violates size constraints; discarded", code="file_rejected")

    mime = getattr(provider, "sniff_mime", lambda k: None)(payload.storage_key)
    if mime is None:
        provider.delete(payload.storage_key)
        raise PreconditionFailed("File content could not be verified as an allowed type; discarded",
                                 code="mime_unverifiable")
    if mime not in ALLOWED_UPLOAD_MIMES:
        provider.delete(payload.storage_key)
        raise PreconditionFailed("File content does not match an allowed document type; discarded",
                                 code="mime_mismatch")

    document = ReleaseDocument(
        project_id=participant.project_id,
        participant_id=participant.id,
        storage_key=payload.storage_key,
        original_filename=Path(payload.storage_key).name.split("_", 1)[-1],
        mime_type=mime,
        file_size=size,
        document_date=payload.document_date,
        signature_status=payload.signature_status,
        extraction_status="pending",
        uploaded_by=user.id,
    )
    db.add(document)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This upload was already finalised", code="already_finalised")
    audit.record(db, project_id=participant.project_id, participant_id=participant.id,
                 actor_type="user", actor_id=str(user.id),
                 action="document.uploaded", entity_type="release_document", entity_id=document.id,
                 new_value={"mime_type": mime, "file_size": size,
                            "signature_status": document.signature_status})
    db.commit()
    db.refresh(document)
    return _doc_out(document)


@router.get("/participants/{participant_id}/documents", response_model=Page[DocumentOut])
def list_documents(participant_id: uuid.UUID, db: DbSession, user: CurrentUser,
                   page: Annotated[PageParams, Depends(page_params)]) -> Page[DocumentOut]:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    membership = get_membership(db, participant.project_id, user)
    is_self = participant.user_id == user.id
    if not is_self and membership.role not in permissions.SENSITIVE_READ_ROLES:
        raise PermissionDenied("Documents are visible to owner, producer, participant-care-lead, or the participant")
    stmt = select(ReleaseDocument).where(ReleaseDocument.participant_id == participant.id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(ReleaseDocument.created_at.desc())
                      .limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[_doc_out(d) for d in rows], total=total, limit=page.limit, offset=page.offset)


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> DocumentOut:
    document = db.get(ReleaseDocument, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    _doc_access(db, document, user)
    return _doc_out(document)


@router.get("/documents/{document_id}/download-url", response_model=DownloadUrlResponse)
def request_download_url(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> DownloadUrlResponse:
    document = db.get(ReleaseDocument, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    _doc_access(db, document, user)
    provider = get_storage_provider()
    url = provider.create_download_url(document.storage_key, ttl_seconds=settings.download_url_ttl_seconds)
    audit.record(db, project_id=document.project_id, participant_id=document.participant_id,
                 actor_type="user", actor_id=str(user.id),
                 action="document.download_url_issued", entity_type="release_document", entity_id=document.id)
    db.commit()
    return DownloadUrlResponse(download_url=url, expires_in_seconds=settings.download_url_ttl_seconds)


@router.post("/documents/{document_id}/extract", response_model=DocumentOut)
def extract_document(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> DocumentOut:
    document = db.get(ReleaseDocument, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    membership = get_membership(db, document.project_id, user)
    if membership.role not in permissions.PARTICIPANT_WRITE_ROLES:
        raise PermissionDenied("This role cannot trigger extraction")
    from app.services import extraction
    document = extraction.extract_document(db, document=document, actor=("user", str(user.id)),
                                           correlation_id=uuid.uuid4())
    db.commit()
    db.refresh(document)
    return _doc_out(document)


@router.post("/documents/{document_id}/propose-consent", status_code=202)
def propose_consent(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> dict:
    document = db.get(ReleaseDocument, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    membership = get_membership(db, document.project_id, user)
    if membership.role not in permissions.PARTICIPANT_WRITE_ROLES:
        raise PermissionDenied("This role cannot propose consent from documents")
    participant = db.get(Participant, document.participant_id)
    from app.services import extraction
    record_id = extraction.propose_consent_from_document(
        db, document=document, participant=participant,
        recorded_by_id=user.id, actor=("user", str(user.id)), correlation_id=uuid.uuid4(),
    )
    db.commit()
    if record_id is None:
        return {"proposed_record_id": None, "detail": "No explicit participant statements detected; nothing proposed."}
    return {"proposed_record_id": str(record_id),
            "detail": "Proposed consent record created; it is UNCONFIRMED until a human confirms it."}
