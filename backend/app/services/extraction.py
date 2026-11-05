"""Document validation + text extraction pipeline (PDF / TXT / MD / DOCX).

Order: validate -> store privately -> extract with page references -> propose
consent findings via the Consent Analyst -> AWAIT HUMAN CONFIRMATION.
Extracted text is untrusted data; it never becomes an agreed choice by itself.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.exceptions import PreconditionFailed
from app.models import DocumentPage, Participant, ReleaseDocument
from app.schemas.consent import ConsentChoiceIn
from app.services import audit, consent_service, document_intelligence

logger = logging.getLogger("scenesteward.extraction")

MAX_PAGES = 500
MAX_TEXT_CHARS = 2_000_000


def _extract_pages(data: bytes, mime: str) -> list[tuple[int, str]]:
    import io

    pages: list[tuple[int, str]] = []
    if mime == "application/pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PreconditionFailed("Encrypted PDFs are not supported for extraction")
        for i, page in enumerate(reader.pages[:MAX_PAGES], start=1):
            text = (page.extract_text() or "").strip()
            pages.append((i, text))
    elif mime in ("text/plain", "text/markdown"):
        pages.append((1, data.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]))
    elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        import docx
        doc = docx.Document(io.BytesIO(data))
        pages.append((1, "\n".join(p.text for p in doc.paragraphs)[:MAX_TEXT_CHARS]))
    else:
        raise PreconditionFailed(f"Unsupported mime type for extraction: {mime}")
    return pages


def extract_document(db: Session, *, document: ReleaseDocument, actor: tuple[str, str],
                     correlation_id: uuid.UUID) -> ReleaseDocument:
    from app.integrations.storage import get_storage_provider
    storage = get_storage_provider()

    document.extraction_status = "processing"
    document.extraction_error = None
    try:
        data = storage.read_bytes(document.storage_key)
        pages = _extract_pages(data, document.mime_type)
    except Exception as exc:  # noqa: BLE001 — any extraction failure must degrade to 'failed', never crash
        document.extraction_status = "failed"
        document.extraction_error = f"{type(exc).__name__}: {str(exc)[:400]}"
        logger.warning("extraction failed document=%s error=%s", document.id, type(exc).__name__)
        from app.events import publish
        publish("document.extraction_failed", correlation_id=correlation_id,
                document_id=str(document.id), error_category=type(exc).__name__)
        audit.record(db, project_id=document.project_id, participant_id=document.participant_id,
                     actor_type=actor[0], actor_id=actor[1],
                     action="document.extraction_failed", entity_type="release_document",
                     entity_id=document.id, new_value={"error_category": type(exc).__name__},
                     correlation_id=correlation_id)
        return document

    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
    total = 0
    all_flags = []
    for number, raw_content in pages:
        clean_text, flags = document_intelligence.sanitize_text(raw_content, page_number=number)
        all_flags.extend(flags)
        total += len(clean_text)
        if total > MAX_TEXT_CHARS:
            break
        db.add(DocumentPage(document_id=document.id, page_number=number, content=clean_text))
    document.extraction_status = "extracted"
    if all_flags:
        audit.record(db, project_id=document.project_id, participant_id=document.participant_id,
                     actor_type=actor[0], actor_id=actor[1],
                     action="document.adversarial_flag_detected", entity_type="release_document",
                     entity_id=document.id,
                     new_value={"flag_count": len(all_flags), "categories": [f.category for f in all_flags]},
                     correlation_id=correlation_id)
    audit.record(db, project_id=document.project_id, participant_id=document.participant_id,
                 actor_type=actor[0], actor_id=actor[1],
                 action="document.extracted", entity_type="release_document", entity_id=document.id,
                 new_value={"pages": len(pages), "sanitized": True, "flags_detected": len(all_flags)},
                 correlation_id=correlation_id)
    return document


def propose_consent_from_document(db: Session, *, document: ReleaseDocument,
                                  participant: Participant, recorded_by_id: uuid.UUID,
                                  actor: tuple[str, str], correlation_id: uuid.UUID) -> uuid.UUID | None:
    """Run the Consent Analyst over extracted pages and save PROPOSED (unconfirmed)
    findings as a new consent record version awaiting human confirmation."""
    if document.extraction_status != "extracted":
        raise PreconditionFailed("Document text has not been extracted yet", code="not_extracted")

    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document.id).order_by(DocumentPage.page_number).all()
    from app.agents.consent_analyst import ConsentAnalystAgent
    from app.services import consent_comparison  # noqa: F401  (kept for symmetry)
    from app.services.agent_context import build_context

    context = build_context(
        agent_name="consent_analyst",
        project_id=document.project_id,
        participant_id=participant.id,
        proposed_use=None,
        story_element=None,
        latest_confirmed=None,
        confirmed_history=[],
        analysis_findings=[],
        analysis_outcome=None,
        document_text=[{"page_number": p.page_number, "content": p.content} for p in pages],
        input_reference=f"document:{document.id}",
    )
    settings_run = ConsentAnalystAgent().execute(db, context=context, actor=actor, correlation_id=correlation_id)
    output = settings_run.output_data or {}

    choices: list[ConsentChoiceIn] = []
    for f in output.get("findings", []):
        category = f.get("category")
        if not category:
            continue
        raw_choice = f.get("choice")
        if raw_choice in ("agreed", "declined"):
            choice = raw_choice
        else:
            choice = "needs_clarification"
        confidence = {"high": 0.8, "medium": 0.6, "low": 0.4}.get(f.get("confidence", "medium"), 0.6)
        refs = ", ".join(f.get("source_references", [])[:3])
        choices.append(ConsentChoiceIn(
            category=category,
            choice=choice,
            explanation=(f.get("finding") or "")[:2000],
            evidence_reference=refs or None,
            source_type="extracted",
            confidence_if_extracted=confidence,
        ))
    if not choices:
        return None

    record = consent_service.create_consent_record(
        db, participant=participant, project_id=document.project_id,
        recorded_by_id=recorded_by_id, source_type="extracted",
        source_document_id=document.id,
        explanation="Proposed choices extracted from document; UNCONFIRMED — human review and participant confirmation required.",
        choices=choices, actor=actor, correlation_id=correlation_id,
        initial_status="awaiting_confirmation",
    )
    return record.id
