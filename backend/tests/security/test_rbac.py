"""RBAC + cross-project isolation — the security perimeter, tested end to end."""
from __future__ import annotations

import pytest

from tests.conftest import add_member, auth_headers, make_project, make_user

ROLES = ["producer", "director", "editor", "participant_care_lead", "viewer"]


@pytest.fixture()
def scenario(db):
    owner = make_user(db, "owner@rbac.test", "Owner One")
    project = make_project(db, owner)
    members = {}
    for role in ROLES:
        u = make_user(db, f"{role}@rbac.test", role.replace("_", " ").title())
        add_member(db, project, u, role)
        members[role] = u
    # a second, completely separate project with its own owner
    outsider = make_user(db, "outsider@rbac.test", "Out Sider")
    other_project = make_project(db, outsider, title="Other Project")
    return {"owner": owner, "project": project, "members": members,
            "outsider": outsider, "other_project": other_project}


def _hdr(user):
    return auth_headers(user)


def test_viewer_cannot_modify_project(client, scenario):
    v = scenario["members"]["viewer"]
    r = client.patch(f"/api/v1/projects/{scenario['project'].id}",
                     json={"title": "Hacked", "expected_version": 1},
                     headers=_hdr(v))
    assert r.status_code == 403


def test_viewer_cannot_create_participant(client, scenario):
    v = scenario["members"]["viewer"]
    r = client.post(f"/api/v1/projects/{scenario['project'].id}/participants",
                    json={"display_name": "Nope"}, headers=_hdr(v))
    assert r.status_code == 403


def test_editor_cannot_read_contacts_but_care_lead_can(client, scenario, db):
    editor = scenario["members"]["editor"]
    care = scenario["members"]["participant_care_lead"]
    owner = scenario["owner"]
    # create a participant + contact as owner
    r = client.post(f"/api/v1/projects/{scenario['project'].id}/participants",
                    json={"display_name": "Contact Person"}, headers=_hdr(owner))
    pid = r.json()["id"]
    r = client.post(f"/api/v1/participants/{pid}/contacts",
                    json={"contact_type": "email", "value": "contact@example.com"},
                    headers=_hdr(owner))
    assert r.status_code == 201

    r = client.get(f"/api/v1/participants/{pid}/contacts", headers=_hdr(editor))
    assert r.status_code == 403  # editors are not granted contact access
    r = client.get(f"/api/v1/participants/{pid}/contacts", headers=_hdr(care))
    assert r.status_code == 200
    assert r.json()[0]["value"] == "contact@example.com"


def test_viewer_cannot_create_consent_record(client, scenario):
    owner = scenario["owner"]
    v = scenario["members"]["viewer"]
    r = client.post(f"/api/v1/projects/{scenario['project'].id}/participants",
                    json={"display_name": "Consent Subject"}, headers=_hdr(owner))
    pid = r.json()["id"]
    r = client.post(f"/api/v1/participants/{pid}/consent-records",
                    json={"source_type": "verbal_recorded",
                          "choices": [{"category": "interview_recording", "choice": "agreed"}]},
                    headers=_hdr(v))
    assert r.status_code == 403


def test_editor_cannot_confirm_consent(client, scenario):
    owner = scenario["owner"]
    editor = scenario["members"]["editor"]
    r = client.post(f"/api/v1/projects/{scenario['project'].id}/participants",
                    json={"display_name": "Confirm Subject"}, headers=_hdr(owner))
    pid = r.json()["id"]
    r = client.post(f"/api/v1/participants/{pid}/consent-records",
                    json={"source_type": "verbal_recorded",
                          "choices": [{"category": "interview_recording", "choice": "agreed"}]},
                    headers=_hdr(owner))
    record_id = r.json()["id"]
    r = client.post(f"/api/v1/consent-records/{record_id}/confirm",
                    json={"confirmation": "confirmed",
                          "confirmation_evidence": "signed release page 2",
                          "expected_version": 1},
                    headers=_hdr(editor))
    assert r.status_code == 403


def test_care_lead_can_confirm_consent(client, scenario):
    owner = scenario["owner"]
    care = scenario["members"]["participant_care_lead"]
    r = client.post(f"/api/v1/projects/{scenario['project'].id}/participants",
                    json={"display_name": "Confirm Two"}, headers=_hdr(owner))
    pid = r.json()["id"]
    r = client.post(f"/api/v1/participants/{pid}/consent-records",
                    json={"source_type": "verbal_recorded",
                          "choices": [{"category": "interview_recording", "choice": "agreed"}]},
                    headers=_hdr(owner))
    record_id = r.json()["id"]
    r = client.post(f"/api/v1/consent-records/{record_id}/confirm",
                    json={"confirmation": "confirmed",
                          "confirmation_evidence": "participant confirmed on camera",
                          "expected_version": 1},
                    headers=_hdr(care))
    assert r.status_code == 200
    assert r.json()["record_status"] == "confirmed"


def test_non_member_cannot_see_project(client, scenario):
    outsider = scenario["outsider"]
    pid = scenario["project"].id
    for url in [f"/api/v1/projects/{pid}",
                f"/api/v1/projects/{pid}/participants",
                f"/api/v1/projects/{pid}/proposed-uses",
                f"/api/v1/projects/{pid}/tasks",
                f"/api/v1/projects/{pid}/timeline"]:
        assert client.get(url, headers=_hdr(outsider)).status_code == 404, url


def test_outsider_cannot_read_other_projects_participant(client, scenario):
    owner = scenario["owner"]
    r = client.post(f"/api/v1/projects/{scenario['project'].id}/participants",
                    json={"display_name": "Private Person"}, headers=_hdr(owner))
    pid = r.json()["id"]
    outsider = scenario["outsider"]
    r = client.get(f"/api/v1/participants/{pid}", headers=_hdr(outsider))
    assert r.status_code == 404


def test_last_owner_cannot_be_demoted_or_removed(client, scenario):
    owner = scenario["owner"]
    pid = scenario["project"].id
    r = client.get(f"/api/v1/projects/{pid}/members", headers=_hdr(owner))
    owner_row = next(m for m in r.json() if m["role"] == "project_owner")
    r = client.patch(f"/api/v1/projects/{pid}/members/{owner_row['id']}",
                     json={"role": "viewer"}, headers=_hdr(owner))
    assert r.status_code == 412
    r = client.delete(f"/api/v1/projects/{pid}/members/{owner_row['id']}",
                      headers=_hdr(owner))
    assert r.status_code == 412


def test_viewer_timeline_hides_sensitive_entries(client, scenario):
    owner = scenario["owner"]
    v = scenario["members"]["viewer"]
    r = client.post(f"/api/v1/projects/{scenario['project'].id}/participants",
                    json={"display_name": "Timeline Subject"}, headers=_hdr(owner))
    pid = r.json()["id"]
    client.post(f"/api/v1/participants/{pid}/consent-records",
                json={"source_type": "verbal_recorded",
                      "choices": [{"category": "interview_recording", "choice": "agreed"}]},
                headers=_hdr(owner))
    r = client.get(f"/api/v1/projects/{scenario['project'].id}/timeline?limit=50",
                   headers=_hdr(v))
    actions = [item["action"] for item in r.json()["items"]]
    assert "consent_record.created" not in actions  # sensitive entity hidden from viewers
    r = client.get(f"/api/v1/projects/{scenario['project'].id}/timeline?limit=50",
                   headers=_hdr(owner))
    actions = [item["action"] for item in r.json()["items"]]
    assert "consent_record.created" in actions
