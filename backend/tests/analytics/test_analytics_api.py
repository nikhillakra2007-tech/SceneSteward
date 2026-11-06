"""API tests for SceneSteward Analytics endpoints.

Verifies:
1. /api/v1/analytics/overview
2. /api/v1/analytics/projects
3. /api/v1/analytics/consent
4. /api/v1/analytics/consent/categories
5. /api/v1/analytics/reviews
6. /api/v1/analytics/operations
7. /api/v1/analytics/withdrawals
8. /api/v1/analytics/advisory
9. /api/v1/analytics/trends
10. /api/v1/analytics/exports (CSV and JSON)
"""
from __future__ import annotations

import uuid

import pytest

from app.core.choices import CONSENT_CATEGORIES
from app.models import ConsentChoice, ConsentRecord, Participant
from tests.conftest import auth_headers, make_project, make_user


@pytest.fixture()
def setup_api_data(db):
    owner = make_user(db, f"api_owner_{uuid.uuid4().hex[:6]}@analytics.test", "Producer Bob")
    project = make_project(db, owner, title="Voices of the Glade")

    p1 = Participant(project_id=project.id, display_name="Amina Diallo", participant_status="active")
    db.add(p1)
    db.commit()

    rec = ConsentRecord(
        participant_id=p1.id,
        project_id=project.id,
        version_number=1,
        record_status="confirmed",
        source_type="interview",
        recorded_by=owner.id,
        participant_confirmation="confirmed",
    )
    db.add(rec)
    db.flush()

    for idx, cat in enumerate(CONSENT_CATEGORIES):
        val = "agreed" if idx < 12 else "declined"
        db.add(ConsentChoice(consent_record_id=rec.id, category=cat, choice=val))
    db.commit()

    return {"owner": owner, "project": project, "p1": p1}


def test_api_analytics_overview(client, setup_api_data):
    owner = setup_api_data["owner"]
    headers = auth_headers(owner)

    resp = client.get("/api/v1/analytics/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_projects"] == 1
    assert data["total_participants"] == 1
    assert data["active_participants"] == 1
    assert data["discussion_coverage"] == 100.0
    assert data["approval_rate"] == 80.0
    assert data["resolution_rate"] == 100.0


def test_api_analytics_consent_and_categories(client, setup_api_data):
    owner = setup_api_data["owner"]
    project = setup_api_data["project"]
    headers = auth_headers(owner)

    resp = client.get(f"/api/v1/analytics/consent?project_id={project.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["categories"]) == 15
    assert data["agreed_choices"] == 12
    assert data["declined_choices"] == 3

    resp_cat = client.get(f"/api/v1/analytics/consent/categories?project_id={project.id}", headers=headers)
    assert resp_cat.status_code == 200
    cats = resp_cat.json()
    assert len(cats) == 15


def test_api_analytics_reviews_and_operations(client, setup_api_data):
    owner = setup_api_data["owner"]
    project = setup_api_data["project"]
    headers = auth_headers(owner)

    resp_rev = client.get(f"/api/v1/analytics/reviews?project_id={project.id}", headers=headers)
    assert resp_rev.status_code == 200

    resp_ops = client.get(f"/api/v1/analytics/operations?project_id={project.id}", headers=headers)
    assert resp_ops.status_code == 200

    resp_withdr = client.get(f"/api/v1/analytics/withdrawals?project_id={project.id}", headers=headers)
    assert resp_withdr.status_code == 200


def test_api_analytics_trends(client, setup_api_data):
    owner = setup_api_data["owner"]
    project = setup_api_data["project"]
    headers = auth_headers(owner)

    resp = client.get(f"/api/v1/analytics/trends?project_id={project.id}&interval=day", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "series" in data


def test_api_analytics_exports_csv_and_json(client, setup_api_data):
    owner = setup_api_data["owner"]
    project = setup_api_data["project"]
    headers = auth_headers(owner)

    # 1. Export Overview CSV
    resp_csv = client.post(
        "/api/v1/analytics/exports",
        json={"project_id": str(project.id), "report_type": "overview", "format": "csv"},
        headers=headers,
    )
    assert resp_csv.status_code == 200
    csv_data = resp_csv.json()
    assert "content" in csv_data
    assert "SceneSteward Analytics Export" in csv_data["content"]
    assert "Total Projects,1" in csv_data["content"]
    assert csv_data["filename"].endswith(".csv")

    # 2. Export Consent Coverage JSON
    resp_json = client.post(
        "/api/v1/analytics/exports",
        json={"project_id": str(project.id), "report_type": "consent_coverage", "format": "json"},
        headers=headers,
    )
    assert resp_json.status_code == 200
    json_data = resp_json.json()
    assert json_data["filename"].endswith(".json")


def test_api_analytics_invalid_date_range_rejected(client, setup_api_data):
    owner = setup_api_data["owner"]
    headers = auth_headers(owner)

    # start_date after end_date
    resp = client.get(
        "/api/v1/analytics/overview?start_date=2026-12-01T00:00:00Z&end_date=2026-01-01T00:00:00Z",
        headers=headers,
    )
    assert resp.status_code == 409  # ConflictError: start_date cannot be after end_date
