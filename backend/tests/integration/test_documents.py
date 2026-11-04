"""Document pipeline over HTTP: signed URLs, sniffing, RBAC, key hygiene."""
from __future__ import annotations

from tests.conftest import add_member, auth_headers, make_project, make_user

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _setup(client, db, owner_name="doco@example.com"):
    owner = make_user(db, owner_name, "Doc Owner")
    project = make_project(db, owner, title="Docs Project")
    r = client.post(f"/api/v1/projects/{project.id}/participants",
                    json={"display_name": "Release Subject"}, headers=auth_headers(owner))
    return owner, project, r.json()["id"]


def test_full_upload_download_roundtrip(client, db):
    owner, _project, pid = _setup(client, db)
    r = client.post(f"/api/v1/participants/{pid}/documents/upload-url",
                    json={"original_filename": "release.pdf", "mime_type": "application/pdf",
                          "file_size": len(PDF_BYTES)},
                    headers=auth_headers(owner))
    assert r.status_code == 201, r.text
    upload = r.json()

    # upload raw bytes to the signed URL (no bearer required — token is the capability)
    r = client.put(upload["upload_url"], content=PDF_BYTES,
                   headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 201

    r = client.post(f"/api/v1/participants/{pid}/documents/complete-upload",
                    json={"storage_key": upload["storage_key"], "signature_status": "signed"},
                    headers=auth_headers(owner))
    assert r.status_code == 201, r.text
    document = r.json()
    assert document["mime_type"] == "application/pdf"
    assert document["extraction_status"] == "pending"

    r = client.get(f"/api/v1/documents/{document['id']}/download-url",
                   headers=auth_headers(owner))
    url = r.json()["download_url"]
    r = client.get(url)
    assert r.status_code == 200
    assert r.content == PDF_BYTES


def test_editor_cannot_upload_or_read_documents(client, db):
    _owner, project, pid = _setup(client, db)
    editor = make_user(db, "doc-editor@example.com", "Doc Editor")
    add_member(db, project, editor, "editor")
    r = client.post(f"/api/v1/participants/{pid}/documents/upload-url",
                    json={"original_filename": "r.pdf", "mime_type": "application/pdf",
                          "file_size": 10},
                    headers=auth_headers(editor))
    assert r.status_code == 403
    r = client.get(f"/api/v1/participants/{pid}/documents", headers=auth_headers(editor))
    assert r.status_code == 403


def test_disallowed_mime_rejected(client, db):
    owner, _project, pid = _setup(client, db)
    r = client.post(f"/api/v1/participants/{pid}/documents/upload-url",
                    json={"original_filename": "evil.exe", "mime_type": "application/x-msdownload",
                          "file_size": 10},
                    headers=auth_headers(owner))
    assert r.status_code == 422


def test_bad_extension_rejected(client, db):
    owner, _project, pid = _setup(client, db)
    r = client.post(f"/api/v1/participants/{pid}/documents/upload-url",
                    json={"original_filename": "notes.exe", "mime_type": "text/plain",
                          "file_size": 10},
                    headers=auth_headers(owner))
    assert r.status_code == 412


def test_oversized_file_rejected(client, db):
    owner, _project, pid = _setup(client, db)
    r = client.post(f"/api/v1/participants/{pid}/documents/upload-url",
                    json={"original_filename": "big.pdf", "mime_type": "application/pdf",
                          "file_size": 30 * 1024 * 1024},
                    headers=auth_headers(owner))
    assert r.status_code == 412


def test_complete_upload_requires_uploaded_file(client, db):
    owner, project, pid = _setup(client, db)
    key = f"{project.id}/{pid}/deadbeef_never_uploaded.pdf"
    r = client.post(f"/api/v1/participants/{pid}/documents/complete-upload",
                    json={"storage_key": key}, headers=auth_headers(owner))
    assert r.status_code == 412


def test_storage_key_traversal_rejected(client, db):
    owner, project, pid = _setup(client, db)
    for bad in ["../../etc/passwd", f"{project.id}/{pid}/../../outside.pdf", "/abs/path.pdf"]:
        r = client.post(f"/api/v1/participants/{pid}/documents/complete-upload",
                        json={"storage_key": bad}, headers=auth_headers(owner))
        assert r.status_code == 412, bad


def test_download_url_requires_signed_token(client, db):
    _setup(client, db)
    r = client.get("/api/v1/storage/local/download/not-a-token")
    assert r.status_code in (412, 422)


def test_malware_file_detected_and_rejected(client, db):
    from app.services.malware_scanner import EICAR_SIGNATURE
    owner, _project, pid = _setup(client, db)

    # 1. Request upload URL for text file containing EICAR
    r = client.post(
        f"/api/v1/participants/{pid}/documents/upload-url",
        json={"original_filename": "infected.txt", "mime_type": "text/plain", "file_size": len(EICAR_SIGNATURE)},
        headers=auth_headers(owner),
    )
    assert r.status_code == 201
    upload = r.json()

    # 2. Upload EICAR bytes
    r = client.put(upload["upload_url"], content=EICAR_SIGNATURE)
    assert r.status_code == 201

    # 3. Complete upload must fail closed with malware_detected
    r = client.post(
        f"/api/v1/participants/{pid}/documents/complete-upload",
        json={"storage_key": upload["storage_key"]},
        headers=auth_headers(owner),
    )
    assert r.status_code == 412
    assert r.json()["error"]["code"] == "malware_detected"


def test_decompression_bomb_rejected(client, db, monkeypatch):
    import io
    import zipfile

    # Build a zip file with uncompressed size exceeding max_uncompressed_bytes
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 2 MB of zeroes compresses to a few hundred bytes
        zf.writestr("word/document.xml", b"\x00" * (2 * 1024 * 1024))
    docx_bytes = buf.getvalue()

    owner, _project, pid = _setup(client, db)

    # Set threshold low for test (1 MB)
    from app.api.v1.endpoints import documents as doc_endpoint
    monkeypatch.setattr(doc_endpoint.settings, "max_uncompressed_bytes", 1024 * 1024)

    r = client.post(
        f"/api/v1/participants/{pid}/documents/upload-url",
        json={
            "original_filename": "bomb.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size": len(docx_bytes),
        },
        headers=auth_headers(owner),
    )
    assert r.status_code == 201
    upload = r.json()

    r = client.put(upload["upload_url"], content=docx_bytes)
    assert r.status_code == 201

    r = client.post(
        f"/api/v1/participants/{pid}/documents/complete-upload",
        json={"storage_key": upload["storage_key"]},
        headers=auth_headers(owner),
    )
    assert r.status_code == 412
    assert r.json()["error"]["code"] == "decompression_bomb"


def test_archive_traversal_rejected(client, db):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../../../evil.sh", b"echo evil")
    bad_zip = buf.getvalue()

    owner, _project, pid = _setup(client, db)
    r = client.post(
        f"/api/v1/participants/{pid}/documents/upload-url",
        json={
            "original_filename": "traversal.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size": len(bad_zip),
        },
        headers=auth_headers(owner),
    )
    assert r.status_code == 201
    upload = r.json()

    r = client.put(upload["upload_url"], content=bad_zip)
    assert r.status_code == 201

    r = client.post(
        f"/api/v1/participants/{pid}/documents/complete-upload",
        json={"storage_key": upload["storage_key"]},
        headers=auth_headers(owner),
    )
    assert r.status_code == 412
    assert r.json()["error"]["code"] == "archive_traversal"


def test_scanner_fail_closed_when_configured(client, db, monkeypatch):
    owner, _project, pid = _setup(client, db)
    clean_txt = b"Clean contract text."

    from app.api.v1.endpoints import documents as doc_endpoint
    from app.services.malware_scanner import ScanResult, ScanStatus

    # Configure scanner to simulate unavailable and fail_closed=True
    monkeypatch.setattr(doc_endpoint.settings, "antivirus_fail_closed", True)
    monkeypatch.setattr(
        "app.api.v1.endpoints.documents.scan_bytes",
        lambda data, settings=None: ScanResult(status=ScanStatus.UNAVAILABLE, scanner="clamav"),
    )

    r = client.post(
        f"/api/v1/participants/{pid}/documents/upload-url",
        json={"original_filename": "clean.txt", "mime_type": "text/plain", "file_size": len(clean_txt)},
        headers=auth_headers(owner),
    )
    assert r.status_code == 201
    upload = r.json()

    r = client.put(upload["upload_url"], content=clean_txt)
    assert r.status_code == 201

    r = client.post(
        f"/api/v1/participants/{pid}/documents/complete-upload",
        json={"storage_key": upload["storage_key"]},
        headers=auth_headers(owner),
    )
    assert r.status_code == 412
    assert r.json()["error"]["code"] == "malware_scanner_unavailable"

