"""Tests for multi-tenant isolation, cross-project boundaries, and participant token security."""
from __future__ import annotations

import uuid

from tests.conftest import auth_headers, make_project, make_user


def test_cross_project_participant_isolation(client, db):
    owner_a = make_user(db, "owner.a@tenant.test", "Owner A")
    owner_b = make_user(db, "owner.b@tenant.test", "Owner B")
    proj_a = make_project(db, owner_a, "Project Alpha")
    proj_b = make_project(db, owner_b, "Project Beta")
    assert proj_b.id is not None

    # Owner A creates Participant A in Project A
    res = client.post(
        f"/api/v1/projects/{proj_a.id}/participants",
        headers=auth_headers(owner_a),
        json={"display_name": "Participant A", "preferred_language": "English"},
    )
    assert res.status_code == 201
    part_a_id = res.json()["id"]

    # Owner B attempts to view Participant A
    res = client.get(
        f"/api/v1/participants/{part_a_id}",
        headers=auth_headers(owner_b),
    )
    assert res.status_code in (403, 404)

    # Owner B attempts to list participants of Project A
    res = client.get(
        f"/api/v1/projects/{proj_a.id}/participants",
        headers=auth_headers(owner_b),
    )
    assert res.status_code in (403, 404)


def test_cross_project_consent_isolation(client, db):
    owner_a = make_user(db, "owner.a.consent@tenant.test", "Owner A")
    owner_b = make_user(db, "owner.b.consent@tenant.test", "Owner B")
    proj_a = make_project(db, owner_a, "Project Alpha")
    proj_b = make_project(db, owner_b, "Project Beta")
    assert proj_b.id is not None

    # Create participant in Project A
    res = client.post(
        f"/api/v1/projects/{proj_a.id}/participants",
        headers=auth_headers(owner_a),
        json={"display_name": "Participant A"},
    )
    part_a_id = res.json()["id"]

    # Owner A records consent
    consent_payload = {
        "source_type": "release_form",
        "choices": [
            {"category": "interview_recording", "choice": "agreed", "source_type": "manual"},
            {"category": "promotional_clips", "choice": "declined", "source_type": "manual"},
        ],
    }
    res = client.post(
        f"/api/v1/participants/{part_a_id}/consent-records",
        headers=auth_headers(owner_a),
        json=consent_payload,
    )
    assert res.status_code == 201

    # Owner B attempts to view consent records of Participant A
    res = client.get(
        f"/api/v1/participants/{part_a_id}/consents",
        headers=auth_headers(owner_b),
    )
    assert res.status_code in (403, 404)

    # Owner B attempts to record consent for Participant A
    res = client.post(
        f"/api/v1/participants/{part_a_id}/consent-records",
        headers=auth_headers(owner_b),
        json=consent_payload,
    )
    assert res.status_code in (403, 404)


def test_cross_project_document_listing_isolation(client, db):
    owner_a = make_user(db, "owner.a.doc@tenant.test", "Owner A")
    owner_b = make_user(db, "owner.b.doc@tenant.test", "Owner B")
    proj_a = make_project(db, owner_a, "Project Alpha")
    proj_b = make_project(db, owner_b, "Project Beta")
    assert proj_b.id is not None

    # Owner A lists documents for Project A
    res = client.get(
        f"/api/v1/projects/{proj_a.id}/documents",
        headers=auth_headers(owner_a),
    )
    assert res.status_code == 200
    assert "items" in res.json()

    # Owner B attempts to list documents for Project A
    res = client.get(
        f"/api/v1/projects/{proj_a.id}/documents",
        headers=auth_headers(owner_b),
    )
    assert res.status_code in (403, 404)


def test_participant_token_mint_and_portal_access(client, db):
    owner = make_user(db, "owner.token@tenant.test", "Owner Care")
    proj = make_project(db, owner, "Project Token")

    res = client.post(
        f"/api/v1/projects/{proj.id}/participants",
        headers=auth_headers(owner),
        json={"display_name": "Token Participant"},
    )
    part_id = res.json()["id"]

    # Issue access token
    res = client.post(
        f"/api/v1/participants/{part_id}/access-token",
        headers=auth_headers(owner),
    )
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Access participant portal with valid token
    res = client.get(
        f"/api/v1/participants/{part_id}/portal-access?token={token}",
    )
    assert res.status_code == 200
    assert res.json()["display_name"] == "Token Participant"

    # Access with invalid token fails
    res = client.get(
        f"/api/v1/participants/{part_id}/portal-access?token=invalid.token.here",
    )
    assert res.status_code in (401, 403)

    # Access another participant's portal with this token fails
    fake_id = str(uuid.uuid4())
    res = client.get(
        f"/api/v1/participants/{fake_id}/portal-access?token={token}",
    )
    assert res.status_code in (403, 404)


def test_participant_clarification_creates_task(client, db):
    owner = make_user(db, "owner.clarify@tenant.test", "Owner Clarify")
    proj = make_project(db, owner, "Project Clarify")

    res = client.post(
        f"/api/v1/projects/{proj.id}/participants",
        headers=auth_headers(owner),
        json={"display_name": "Clarification Participant"},
    )
    part_id = res.json()["id"]

    # Issue token
    t_res = client.post(
        f"/api/v1/participants/{part_id}/access-token",
        headers=auth_headers(owner),
    )
    token = t_res.json()["access_token"]

    # Participant submits clarification request
    clarify_res = client.post(
        f"/api/v1/participants/{part_id}/clarification-requests?token={token}",
        json={
            "concern": "I am concerned about location disclosure in promotional trailers.",
            "category": "location_disclosure",
        },
    )
    assert clarify_res.status_code == 201
    data = clarify_res.json()
    assert data["status"] == "received"
    assert "task_id" in data

    # Verify task was created in project
    task_res = client.get(
        f"/api/v1/projects/{proj.id}/tasks",
        headers=auth_headers(owner),
    )
    assert task_res.status_code == 200
    tasks = task_res.json()["items"]
    assert any("location disclosure" in t["description"] for t in tasks)
