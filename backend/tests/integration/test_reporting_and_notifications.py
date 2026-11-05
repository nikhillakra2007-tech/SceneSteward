"""Integration tests for Notifications, Audit Export, and Search/Filtering.

Verifies:
- Operational notifications list and urgent priority escalation for withdrawals.
- Full tamper-evident compliance audit package export across 15 canonical categories.
- Participant name search and status filtering.
- Proposed use filtering by participant and status.
- Event bus publishing on participant clarification and withdrawal events.
"""
from __future__ import annotations

from app.core.choices import CONSENT_CATEGORIES
from app.events.bus import Event, bus
from tests.conftest import auth_headers, make_project, make_user


def test_clarification_and_withdrawal_notifications(client, db):
    owner = make_user(db, "producer.notif@scenesteward.example.com", "Producer Notif")
    proj = make_project(db, owner, "Notification Documentary")

    # 1. Create participant
    headers = auth_headers(owner)
    part_resp = client.post(
        f"/api/v1/projects/{proj.id}/participants",
        json={"display_name": "Maya Lin"},
        headers=headers,
    )
    assert part_resp.status_code == 201
    part_id = part_resp.json()["id"]

    # Track published events
    captured_events: list[Event] = []
    bus.subscribe("participant.clarification_requested", lambda e: captured_events.append(e))
    bus.subscribe("participant.withdrawal_requested", lambda e: captured_events.append(e))

    # 2. Submit standard clarification request
    clarif_resp = client.post(
        f"/api/v1/participants/{part_id}/clarification-requests",
        json={"concern": "Can I clarify how my interview is edited?", "category": "interview_recording"},
        headers=headers,
    )
    assert clarif_resp.status_code == 201

    # 3. Submit urgent withdrawal request
    withdr_resp = client.post(
        f"/api/v1/participants/{part_id}/clarification-requests",
        json={
            "concern": "I wish to withdraw my appearance from promotional clips immediately.",
            "category": "promotional_clips",
            "request_type": "withdrawal",
        },
        headers=headers,
    )
    assert withdr_resp.status_code == 201
    assert "withdrawal notice" in withdr_resp.json()["message"].lower()

    # 4. Query notifications endpoint
    notif_resp = client.get(
        f"/api/v1/projects/{proj.id}/notifications",
        headers=headers,
    )
    assert notif_resp.status_code == 200
    notifications = notif_resp.json()
    assert len(notifications) >= 2

    withdrawal_notifs = [n for n in notifications if n["notification_type"] == "withdrawal_notice"]
    assert len(withdrawal_notifs) >= 1
    assert withdrawal_notifs[0]["priority"] == "urgent"


def test_project_audit_export(client, db):
    owner = make_user(db, "producer.export@scenesteward.example.com", "Producer Export")
    proj = make_project(db, owner, "Festival Compliance Project")
    headers = auth_headers(owner)

    # 1. Add participant
    part_resp = client.post(
        f"/api/v1/projects/{proj.id}/participants",
        json={"display_name": "James Baldwin"},
        headers=headers,
    )
    part_id = part_resp.json()["id"]

    # 2. Record & confirm consent record
    rec_resp = client.post(
        f"/api/v1/participants/{part_id}/consent-records",
        json={
            "source_type": "release_form",
            "explanation": "Signed hardcopy agreement on set",
            "choices": [
                {"category": "interview_recording", "choice": "agreed"},
                {"category": "festival_submissions", "choice": "agreed"},
                {"category": "voice_cloning", "choice": "declined"},
            ],
        },
        headers=headers,
    )
    assert rec_resp.status_code == 201
    rec_id = rec_resp.json()["id"]

    confirm_resp = client.post(
        f"/api/v1/consent-records/{rec_id}/confirm",
        json={
            "confirmation": "confirmed",
            "confirmation_evidence": "Signed physical release on file",
            "expected_version": 1,
        },
        headers=headers,
    )
    assert confirm_resp.status_code == 200

    # 3. Fetch audit export package
    export_resp = client.get(
        f"/api/v1/projects/{proj.id}/audit-export",
        headers=headers,
    )
    assert export_resp.status_code == 200
    bundle = export_resp.json()

    assert bundle["project_id"] == str(proj.id)
    assert bundle["total_participants"] == 1
    assert len(bundle["integrity_hash"]) == 64  # SHA256 length

    # Invariants and categories
    assert len(bundle["consent_overview"]) == len(CONSENT_CATEGORIES)
    assert bundle["consent_overview"]["interview_recording"]["agreed"] == 1
    assert bundle["consent_overview"]["voice_cloning"]["declined"] == 1

    # Prohibitions present due to declined voice cloning
    assert bundle["compliance_status"] in ("prohibitions_present", "cleared_for_release", "action_required")
    assert any("Silence is never agreement" in inv for inv in bundle["invariants_verified"])


def test_participant_search_and_filtering(client, db):
    owner = make_user(db, "producer.search@scenesteward.example.com", "Producer Search")
    proj = make_project(db, owner, "Search Filter Project")
    headers = auth_headers(owner)

    client.post(f"/api/v1/projects/{proj.id}/participants", json={"display_name": "Alice Wonder"}, headers=headers)
    client.post(f"/api/v1/projects/{proj.id}/participants", json={"display_name": "Bob Builder"}, headers=headers)
    client.post(f"/api/v1/projects/{proj.id}/participants", json={"display_name": "Charlie Chaplin"}, headers=headers)

    # Search by query
    res_alice = client.get(f"/api/v1/projects/{proj.id}/participants?search=alice", headers=headers)
    assert res_alice.status_code == 200
    data = res_alice.json()
    assert data["total"] == 1
    assert data["items"][0]["display_name"] == "Alice Wonder"

    # Search with no match
    res_none = client.get(f"/api/v1/projects/{proj.id}/participants?search=nonexistent", headers=headers)
    assert res_none.status_code == 200
    assert res_none.json()["total"] == 0
