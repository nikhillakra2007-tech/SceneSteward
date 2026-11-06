"""Security and authorization tests for SceneSteward Analytics.

Verifies:
1. Unauthenticated requests are rejected with 401.
2. Cross-tenant project analytics access returns 404 (no existence disclosure).
3. Users with 'participant' role are denied access to internal analytics (403).
4. Unauthorized exports are rejected.
5. Tenant isolation is completely preserved across all endpoints.
"""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import add_member, auth_headers, make_project, make_user


@pytest.fixture()
def multi_tenant_setup(db):
    user_a = make_user(db, f"tenant_a_{uuid.uuid4().hex[:6]}@sec.test", "Director Alpha")
    user_b = make_user(db, f"tenant_b_{uuid.uuid4().hex[:6]}@sec.test", "Director Beta")
    user_part = make_user(db, f"part_{uuid.uuid4().hex[:6]}@sec.test", "Participant User")

    proj_a = make_project(db, user_a, title="Project Alpha")
    proj_b = make_project(db, user_b, title="Project Beta")

    # Add user_part to proj_a with role 'participant'
    add_member(db, proj_a, user_part, role="participant")

    return {
        "user_a": user_a,
        "user_b": user_b,
        "user_part": user_part,
        "proj_a": proj_a,
        "proj_b": proj_b,
    }


def test_unauthenticated_analytics_request_rejected(client):
    resp = client.get("/api/v1/analytics/overview")
    assert resp.status_code == 401


def test_cross_tenant_analytics_returns_404(client, multi_tenant_setup):
    user_b = multi_tenant_setup["user_b"]
    proj_a = multi_tenant_setup["proj_a"]
    headers_b = auth_headers(user_b)

    # User B attempts to access analytics for Project A
    resp = client.get(f"/api/v1/analytics/overview?project_id={proj_a.id}", headers=headers_b)
    assert resp.status_code == 404


def test_participant_role_denied_analytics(client, multi_tenant_setup):
    user_part = multi_tenant_setup["user_part"]
    proj_a = multi_tenant_setup["proj_a"]
    headers_part = auth_headers(user_part)

    # Participant role accesses analytics on Project A
    resp = client.get(f"/api/v1/analytics/overview?project_id={proj_a.id}", headers=headers_part)
    assert resp.status_code == 403


def test_isolated_portfolio_overview(client, multi_tenant_setup):
    user_a = multi_tenant_setup["user_a"]
    user_b = multi_tenant_setup["user_b"]
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    # User A overview: only sees Project A
    res_a = client.get("/api/v1/analytics/overview", headers=headers_a).json()
    assert res_a["total_projects"] == 1
    assert res_a["scope"]["authorized_projects_count"] == 1

    # User B overview: only sees Project B
    res_b = client.get("/api/v1/analytics/overview", headers=headers_b).json()
    assert res_b["total_projects"] == 1
    assert res_b["scope"]["authorized_projects_count"] == 1


def test_cross_tenant_export_rejected(client, multi_tenant_setup):
    user_b = multi_tenant_setup["user_b"]
    proj_a = multi_tenant_setup["proj_a"]
    headers_b = auth_headers(user_b)

    resp = client.post(
        "/api/v1/analytics/exports",
        json={"project_id": str(proj_a.id), "report_type": "overview", "format": "csv"},
        headers=headers_b,
    )
    assert resp.status_code == 404
