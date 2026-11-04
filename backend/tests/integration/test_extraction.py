"""Document processing pipeline — end to end on real files (PDF/TXT).

Proves: validate → store → extract (page refs) → propose UNCONFIRMED consent
findings → human confirmation gate; corrupt files degrade to 'failed' with an
error record; nothing is auto-confirmed.
"""
from __future__ import annotations

import io
import uuid

from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.models import AuditEvent, DocumentPage
from tests.conftest import add_member, auth_headers, make_project, make_user

LINES = [
    "I agree to the interview recording.",
    "I do not consent to voice cloning.",
    "The trailer situation is maybe okay?",
]


def make_pdf(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 780
    for line in lines:
        c.drawString(72, y, line)
        y -= 24
    c.showPage()
    c.save()
    return buf.getvalue()


def _upload(client, db, owner, project, participant_id, filename, mime, data):
    r = client.post(f"/api/v1/participants/{participant_id}/documents/upload-url",
                    json={"original_filename": filename, "mime_type": mime,
                          "file_size": len(data)},
                    headers=auth_headers(owner))
    assert r.status_code == 201, r.text
    up = r.json()
    r = client.put(up["upload_url"], content=data, headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 201
    r = client.post(f"/api/v1/participants/{participant_id}/documents/complete-upload",
                    json={"storage_key": up["storage_key"], "signature_status": "signed"},
                    headers=auth_headers(owner))
    assert r.status_code == 201, r.text
    return r.json()


def _setup(client, db):
    owner = make_user(db, "ext@example.com", "Extract Owner")
    project = make_project(db, owner, title="Extraction Project")
    r = client.post(f"/api/v1/projects/{project.id}/participants",
                    json={"display_name": "Release Subject"}, headers=auth_headers(owner))
    pid = r.json()["id"]
    return owner, project, pid


def test_pdf_extract_and_propose_unconfirmed_consent(client, db):
    owner, project, pid = _setup(client, db)
    pdf = make_pdf(LINES)
    doc = _upload(client, db, owner, project, pid, "release.pdf", "application/pdf", pdf)
    doc_id = doc["id"]

    r = client.post(f"/api/v1/documents/{doc_id}/extract", headers=auth_headers(owner))
    assert r.status_code == 200, r.text
    assert r.json()["extraction_status"] == "extracted"

    pages = db.execute(select(DocumentPage).where(DocumentPage.document_id == uuid.UUID(doc_id))).scalars().all()
    assert len(pages) == 1
    extracted = " ".join(p.content for p in pages)
    assert "interview" in extracted.lower()

    r = client.post(f"/api/v1/documents/{doc_id}/propose-consent", headers=auth_headers(owner))
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["proposed_record_id"]

    from app.models import ConsentRecord
    record = db.get(ConsentRecord, uuid.UUID(body["proposed_record_id"]))
    assert record.source_type == "extracted"
    assert record.record_status == "awaiting_confirmation"
    assert record.participant_confirmation == "unconfirmed"
    assert record.confirmed_at is None
    assert all(c.confirmed_by is None and c.confirmed_at is None for c in record.choices)
    # every proposed choice carries a page reference and a confidence
    assert all(c.evidence_reference for c in record.choices)
    assert any(c.choice == "agreed" for c in record.choices)      # interview agreement detected
    assert any(c.choice == "declined" for c in record.choices)    # voice-cloning refusal detected

    # the comparison engine only consumes CONFIRMED records: v-anything extracted is ignored
    latest_confirmed = db.execute(
        select(ConsentRecord).where(ConsentRecord.participant_id == uuid.UUID(pid),
                                    ConsentRecord.record_status == "confirmed")).scalars().all()
    assert latest_confirmed == []


def test_corrupt_pdf_degrades_to_failed_with_error(client, db):
    owner, project, pid = _setup(client, db)
    bad = b"%PDF-1.4\n%%EOF garbage-not-a-real-pdf-body-at-all"
    doc = _upload(client, db, owner, project, pid, "broken.pdf", "application/pdf", bad)
    r = client.post(f"/api/v1/documents/{doc['id']}/extract", headers=auth_headers(owner))
    assert r.status_code == 200
    assert r.json()["extraction_status"] == "failed"
    assert r.json()["extraction_error"]

    rows = db.execute(select(AuditEvent).where(
        AuditEvent.entity_id == uuid.UUID(doc["id"]),
        AuditEvent.action == "document.extraction_failed")).scalars().all()
    assert rows, "extraction failure must be auditable"


def test_txt_document_extracts(client, db):
    owner, project, pid = _setup(client, db)
    text_bytes = b"I agree to the interview recording.\nI do not consent to voice cloning.\n"
    doc = _upload(client, db, owner, project, pid, "notes.txt", "text/plain", text_bytes)
    r = client.post(f"/api/v1/documents/{doc['id']}/extract", headers=auth_headers(owner))
    assert r.json()["extraction_status"] == "extracted"
    r = client.post(f"/api/v1/documents/{doc['id']}/propose-consent", headers=auth_headers(owner))
    assert r.status_code == 202
    assert r.json()["proposed_record_id"]


def test_editor_cannot_extract_or_propose(client, db):
    owner, project, pid = _setup(client, db)
    editor = make_user(db, "ext-editor@example.com", "Ext Editor")
    add_member(db, project, editor, "editor")
    pdf = make_pdf(LINES)
    doc = _upload(client, db, owner, project, pid, "r.pdf", "application/pdf", pdf)
    r = client.post(f"/api/v1/documents/{doc['id']}/extract", headers=auth_headers(editor))
    assert r.status_code == 403
    r = client.post(f"/api/v1/documents/{doc['id']}/propose-consent", headers=auth_headers(editor))
    assert r.status_code == 403


def test_extracted_record_requires_human_confirmation(client, db):
    owner, project, pid = _setup(client, db)
    care = make_user(db, "ext-care@example.com", "Ext Care")
    add_member(db, project, care, "participant_care_lead")
    pdf = make_pdf(LINES)
    doc = _upload(client, db, owner, project, pid, "confirm-me.pdf", "application/pdf", pdf)
    client.post(f"/api/v1/documents/{doc['id']}/extract", headers=auth_headers(owner))
    r = client.post(f"/api/v1/documents/{doc['id']}/propose-consent", headers=auth_headers(owner))
    record_id = r.json()["proposed_record_id"]

    # editor (viewer) cannot confirm
    editor = make_user(db, "ext-ed2@example.com", "Ext Ed Two")
    add_member(db, project, editor, "editor")
    r = client.post(f"/api/v1/consent-records/{record_id}/confirm",
                    json={"confirmation": "confirmed", "confirmation_evidence": "tried by editor",
                          "expected_version": 1},
                    headers=auth_headers(editor))
    assert r.status_code == 403

    # care lead can confirm with explicit evidence; record then locks
    r = client.post(f"/api/v1/consent-records/{record_id}/confirm",
                    json={"confirmation": "confirmed", "confirmation_evidence": "participant confirmed on camera",
                          "expected_version": 1},
                    headers=auth_headers(care))
    assert r.status_code == 200
    assert r.json()["record_status"] == "confirmed"
    assert r.json()["participant_confirmation"] == "confirmed"
