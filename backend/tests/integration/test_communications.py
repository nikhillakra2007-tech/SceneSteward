"""Integration tests for participant communications workflow and audit trails."""
from __future__ import annotations

from sqlalchemy import select

from app.models.audit import AuditEvent
from tests.conftest import add_member, auth_headers, make_project, make_user


def _setup(client, db):
    owner = make_user(db, "comm_owner@example.com", "Comm Owner")
    project = make_project(db, owner, title="Comm Project")
    r = client.post(
        f"/api/v1/projects/{project.id}/participants",
        json={"display_name": "Target Participant"},
        headers=auth_headers(owner),
    )
    assert r.status_code == 201
    return owner, project, r.json()["id"]


def test_communication_lifecycle_approval_and_send(client, db):
    _owner, project, pid = _setup(client, db)
    producer = make_user(db, "comm_producer@example.com", "Comm Producer")
    add_member(db, project, producer, "producer")

    editor = make_user(db, "comm_editor@example.com", "Comm Editor")
    add_member(db, project, editor, "editor")

    # 1. Producer drafts communication
    res = client.post(
        f"/api/v1/projects/{project.id}/communications",
        json={
            "participant_id": pid,
            "communication_type": "email",
            "subject": "Discussion on promotional excerpt",
            "draft_content": "Dear Participant, we would like to discuss...",
        },
        headers=auth_headers(producer),
    )
    assert res.status_code == 201
    comm = res.json()
    assert comm["communication_status"] == "draft"
    comm_id = comm["id"]

    # 2. Cannot send draft without human approval
    send_res = client.post(f"/api/v1/communications/{comm_id}/send", headers=auth_headers(producer))
    assert send_res.status_code == 412
    assert send_res.json()["error"]["code"] == "approval_required"

    # 3. Editor cannot approve (denied by RLS/404 or RBAC/403: only owner, producer, or care lead)
    appr_res = client.post(f"/api/v1/communications/{comm_id}/approve", json={}, headers=auth_headers(editor))
    assert appr_res.status_code in (403, 404)

    # 4. Producer approves communication
    appr_res = client.post(f"/api/v1/communications/{comm_id}/approve", json={"notes": "Approved by Priya"}, headers=auth_headers(producer))
    assert appr_res.status_code == 200
    assert appr_res.json()["communication_status"] == "approved"
    assert appr_res.json()["approved_by"] == str(producer.id)

    # 5. Send attempted fails closed with 503 no_provider_configured (never marks sent)
    send_res = client.post(f"/api/v1/communications/{comm_id}/send", headers=auth_headers(producer))
    assert send_res.status_code == 503
    assert send_res.json()["error"]["code"] == "no_provider_configured"

    # Verify status in database remains "approved", not "sent"
    list_res = client.get(f"/api/v1/projects/{project.id}/communications", headers=auth_headers(producer))
    assert list_res.status_code == 200, list_res.text
    assert list_res.json()[0]["communication_status"] == "approved"


def test_contact_read_audit_logging(client, db):
    owner, _project, pid = _setup(client, db)

    # Add contact record
    add_res = client.post(
        f"/api/v1/participants/{pid}/contacts",
        json={"contact_type": "phone", "value": "+1-555-0100"},
        headers=auth_headers(owner),
    )
    assert add_res.status_code == 201

    # Read contacts
    read_res = client.get(f"/api/v1/participants/{pid}/contacts", headers=auth_headers(owner))
    assert read_res.status_code == 200
    assert len(read_res.json()) == 1

    # Verify audit event recorded
    audit_rows = db.execute(
        select(AuditEvent).where(
            AuditEvent.action == "participant_contact.read",
            AuditEvent.participant_id == pid,
        )
    ).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].new_value["contact_count"] == 1
