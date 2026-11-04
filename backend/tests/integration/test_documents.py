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
