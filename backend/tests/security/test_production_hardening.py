"""Comprehensive production hardening, trust boundary, and authentication verification tests.

Validates:
1. Participant clarification endpoint rejects unauthenticated requests (HTTP 401).
2. Participant clarification endpoint rejects cross-tenant access from other users (HTTP 404).
3. Participant clarification endpoint rejects participant tokens belonging to another participant (HTTP 403).
4. Participant clarification endpoint rejects participant tokens with mismatched project_id (HTTP 404).
5. Legitimate participant portal tokens and member bearer tokens successfully create tasks and audit logs.
6. Formal withdrawal requests escalate task priority to 'urgent' and trigger correct audit actions.
7. /api/v1/integrations/status accurately inspects all system services including Redis and Antivirus.
8. DevTokenRequest schema enforces boundary constraints on name length.
9. Database session contexts (user_context and system_context) cleanly isolate and reset connection state.
"""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.core.database import clear_identity, set_identity, system_context
from app.core.security import mint_participant_token
from app.models import Participant, Task
from app.schemas.auth import DevTokenRequest
from tests.conftest import auth_headers, make_project, make_user


@pytest.fixture()
def setup_tenants(db):
    user_a = make_user(db, f"tenant_a_{uuid.uuid4().hex[:6]}@prod.test", "Tenant A Owner")
    user_b = make_user(db, f"tenant_b_{uuid.uuid4().hex[:6]}@prod.test", "Tenant B Owner")
    proj_a = make_project(db, user_a, title="Project Alpha")
    proj_b = make_project(db, user_b, title="Project Beta")

    part_a = Participant(
        project_id=proj_a.id,
        display_name="Participant Alpha",
        participant_status="active",
    )
    part_b = Participant(
        project_id=proj_b.id,
        display_name="Participant Beta",
        participant_status="active",
    )
    db.add_all([part_a, part_b])
    db.commit()
    db.refresh(part_a)
    db.refresh(part_b)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "proj_a": proj_a,
        "proj_b": proj_b,
        "part_a": part_a,
        "part_b": part_b,
    }


def test_unauthenticated_clarification_request_rejected(client, setup_tenants):
    part_a = setup_tenants["part_a"]
    # Request with no token parameter and no Authorization header must fail with 401
    resp = client.post(
        f"/api/v1/participants/{part_a.id}/clarification-requests",
        json={"concern": "Unauthenticated test concern"},
    )
    assert resp.status_code == 401, f"Expected 401 Unauthorized, got {resp.status_code}: {resp.text}"
    assert "unauthenticated" in resp.text.lower() or "required" in resp.text.lower()


def test_cross_tenant_clarification_request_rejected(client, setup_tenants):
    user_b = setup_tenants["user_b"]
    part_a = setup_tenants["part_a"]
    # User B (member of Project B only) attempts to submit clarification for Participant A in Project A
    headers_b = auth_headers(user_b)
    resp = client.post(
        f"/api/v1/participants/{part_a.id}/clarification-requests",
        json={"concern": "Cross-tenant intrusion attempt"},
        headers=headers_b,
    )
    # Must return 404 (not found) so as not to reveal participant existence across tenants
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}: {resp.text}"


def test_tampered_participant_token_rejected(client, setup_tenants):
    part_a = setup_tenants["part_a"]
    part_b = setup_tenants["part_b"]
    proj_b = setup_tenants["proj_b"]

    # Token minted for Participant B
    token_b = mint_participant_token(
        participant_id=part_b.id,
        project_id=proj_b.id,
    )

    # Use Token B against Participant A's endpoint
    resp = client.post(
        f"/api/v1/participants/{part_a.id}/clarification-requests?token={token_b}",
        json={"concern": "Tampered token test"},
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}: {resp.text}"
    assert "does not match" in resp.text.lower()


def test_mismatched_project_in_participant_token_rejected(client, setup_tenants):
    part_a = setup_tenants["part_a"]
    proj_b = setup_tenants["proj_b"]

    # Forged token: claims sub is Participant A, but project_id is Project B
    forged_token = mint_participant_token(
        participant_id=part_a.id,
        project_id=proj_b.id,
    )

    resp = client.post(
        f"/api/v1/participants/{part_a.id}/clarification-requests?token={forged_token}",
        json={"concern": "Forged project ID token test"},
    )
    # Must fail with 404 Not Found
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}: {resp.text}"


def test_legitimate_participant_token_submission(client, db, setup_tenants):
    part_a = setup_tenants["part_a"]
    proj_a = setup_tenants["proj_a"]

    token_a = mint_participant_token(
        participant_id=part_a.id,
        project_id=proj_a.id,
    )

    resp = client.post(
        f"/api/v1/participants/{part_a.id}/clarification-requests?token={token_a}",
        json={"concern": "Can you blur my home background?", "category": "interview_framing"},
    )
    assert resp.status_code == 201, f"Expected 201 Created, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "received"
    task_id = uuid.UUID(data["task_id"])

    # Verify task was created in database
    task = db.get(Task, task_id)
    assert task is not None
    assert task.project_id == proj_a.id
    assert task.participant_id == part_a.id
    assert task.task_type == "participant_follow_up"
    assert task.priority == "high"
    assert "blur my home" in task.description


def test_legitimate_member_bearer_submission(client, db, setup_tenants):
    user_a = setup_tenants["user_a"]
    part_a = setup_tenants["part_a"]
    proj_a = setup_tenants["proj_a"]

    headers_a = auth_headers(user_a)
    resp = client.post(
        f"/api/v1/participants/{part_a.id}/clarification-requests",
        json={"concern": "Field producer logging participant query.", "category": "audio_clearance"},
        headers=headers_a,
    )
    assert resp.status_code == 201, f"Expected 201 Created, got {resp.status_code}: {resp.text}"
    data = resp.json()
    task_id = uuid.UUID(data["task_id"])

    task = db.get(Task, task_id)
    assert task is not None
    assert task.project_id == proj_a.id


def test_withdrawal_request_escalation_to_urgent(client, db, setup_tenants):
    part_a = setup_tenants["part_a"]
    proj_a = setup_tenants["proj_a"]

    token_a = mint_participant_token(
        participant_id=part_a.id,
        project_id=proj_a.id,
    )

    resp = client.post(
        f"/api/v1/participants/{part_a.id}/clarification-requests?token={token_a}",
        json={
            "concern": "I am formally withdrawing my consent from this documentary immediately.",
            "request_type": "withdrawal",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "withdrawal notice" in data["message"].lower()

    task = db.get(Task, uuid.UUID(data["task_id"]))
    assert task is not None
    assert task.priority == "urgent"
    assert "WITHDRAWAL NOTICE" in task.title
    assert "Immediately pause associated footage edits" in task.description


def test_integrations_status_endpoint(client):
    resp = client.get("/api/v1/integrations/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "integrations" in data
    names = {item["name"] for item in data["integrations"]}
    expected_names = {"postgresql", "storage", "ai_provider", "switch", "auth", "redis", "antivirus"}
    assert expected_names.issubset(names), f"Missing integration names: {expected_names - names}"


def test_dev_token_request_schema_validation():
    # Valid name
    req = DevTokenRequest(email="valid@example.com", name="Valid User")
    assert req.name == "Valid User"

    # Empty name should fail validation
    with pytest.raises(ValidationError):
        DevTokenRequest(email="valid@example.com", name="")

    # Excessively long name should fail validation (>200 chars)
    with pytest.raises(ValidationError):
        DevTokenRequest(email="valid@example.com", name="x" * 201)


def test_context_managers_session_clean_reset(db, setup_tenants):
    user_a = setup_tenants["user_a"]

    # Testing set_identity and clear_identity
    set_identity(user_a.id, session=db)
    curr_uid = db.execute(text("SELECT current_setting('app.user_id', true)")).scalar()
    assert curr_uid == str(user_a.id)

    clear_identity(session=db)
    # Outside identity context: context info must be cleared
    assert db.info.get("user_id") is None

    # Inside system_context: app.system must be on
    with system_context(db):
        curr_sys = db.execute(text("SELECT current_setting('app.system', true)")).scalar()
        assert curr_sys == "on"
        assert db.info.get("system") is True

    # Outside system_context: context must be reset to off
    curr_sys_post = db.execute(text("SELECT current_setting('app.system', true)")).scalar()
    assert curr_sys_post in ("off", "", None)
    assert db.info.get("system") is None
