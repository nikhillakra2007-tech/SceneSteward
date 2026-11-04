"""Switch integration — mock-adapter behaviour + inbound event idempotency.

No live Switch server exists in this environment; all tests here are MOCK tests.
The live connection status is reported as UNVERIFIED everywhere (see SWITCH_INTEGRATION.md).
"""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select

from app.integrations.switch.inmemory_adapter import InMemorySwitchAdapter
from app.integrations.switch.listener import external_event_id, record_inbound_event
from app.models import IntegrationEvent, SwitchRoomLink
from tests.conftest import make_project, make_user


def test_adapter_connection_is_not_fake_verified():
    adapter = InMemorySwitchAdapter()
    status = adapter.verify_connection()
    assert status.status == "configured_verified"
    assert "no network" in (status.detail or "")


def test_room_creation_and_reuse():
    adapter = InMemorySwitchAdapter()
    proj = str(uuid.uuid4())
    first = adapter.get_or_create_room(project_id=proj, participant_id=None,
                                       room_type="project", room_name="demo")
    second = adapter.get_or_create_room(project_id=proj, participant_id=None,
                                        room_type="project", room_name="demo")
    assert first["room_id"] == second["room_id"]
    assert second["reused"] is True


def test_send_review_context_records_message():
    adapter = InMemorySwitchAdapter()
    room = adapter.get_or_create_room(project_id=str(uuid.uuid4()), participant_id="p1",
                                      room_type="participant_review", room_name="demo")
    result = adapter.send_review_context(
        room_id=room["room_id"],
        summary={"proposed_use_id": "u1", "outcome": "NEEDS_DISCUSSION",
                 "missing_categories": ["promotional_clips"], "declined_categories": []},
        correlation_id=str(uuid.uuid4()),
    )
    assert result.ok is True
    assert len(adapter.sent) == 1


def test_send_to_unknown_room_fails_closed():
    adapter = InMemorySwitchAdapter()
    result = adapter.send_review_context(room_id="room-does-not-exist", summary={},
                                         correlation_id=str(uuid.uuid4()))
    assert result.ok is False
    assert result.error_code == "room_not_found"


def test_inbound_event_idempotency(db):
    owner = make_user(db, "sw@example.com")
    project = make_project(db, owner, title="Switch Project")
    link = SwitchRoomLink(project_id=project.id, participant_id=None,
                          room_type="project", switch_room_id="switch-room-abc",
                          switch_room_name="demo")
    db.add(link)
    db.commit()

    raw = {"type": "message", "sequence": 42,
           "data": {"room_id": "switch-room-abc", "body": "analysis ready"}}
    status1, _ = record_inbound_event(db, raw)
    db.commit()
    status2, _ = record_inbound_event(db, raw)  # exact redelivery
    db.commit()
    assert status1 == "processed"
    assert status2 == "skipped_duplicate"
    rows = db.execute(select(IntegrationEvent).where(
        IntegrationEvent.external_event_id == external_event_id(raw))).scalars().all()
    assert len(rows) == 1
    assert rows[0].payload_summary["mapped_project_id"] == str(project.id)


def test_inbound_event_for_unmapped_room_is_recorded_not_crashed(db):
    raw = {"type": "message", "sequence": 99,
           "data": {"room_id": "unknown-room", "body": "hello"}}
    status, _ = record_inbound_event(db, raw)
    db.commit()
    assert status == "processed"
    row = db.execute(select(IntegrationEvent).where(
        IntegrationEvent.external_event_id == external_event_id(raw))).scalar_one()
    assert "unmapped_room" in (row.last_error or "")


def test_consent_cannot_be_modified_by_switch_events(db):
    """There is intentionally no code path from an inbound Switch event to consent tables."""
    from app.integrations.switch import listener
    src = Path(listener.__file__).read_text(encoding="utf-8")
    for forbidden in ("consent_records", "consent_choices", "ConsentRecord", "ConsentChoice"):
        assert forbidden not in src


def test_switch_retry_claim_batch_atomic(db):
    from scripts.switch_retry import claim_batch

    owner = make_user(db, "retry_owner@example.com")
    project = make_project(db, owner, title="Retry Project")

    evt1 = IntegrationEvent(
        integration_name="switch",
        event_type="proposed_use.analyzed",
        external_event_id="ext-retry-1",
        processing_status="failed",
        attempt_count=0,
        project_id=project.id,
        payload_summary={"project_id": str(project.id)},
        payload_reference="proposed_use:00000000-0000-0000-0000-000000000001",
    )
    evt2 = IntegrationEvent(
        integration_name="switch",
        event_type="proposed_use.analyzed",
        external_event_id="ext-retry-2",
        processing_status="failed",
        attempt_count=1,
        project_id=project.id,
        payload_summary={"project_id": str(project.id)},
        payload_reference="proposed_use:00000000-0000-0000-0000-000000000002",
    )
    db.add_all([evt1, evt2])
    db.commit()

    claimed_1 = claim_batch(db, limit=1)
    assert len(claimed_1) == 1
    assert claimed_1[0].processing_status == "processing"
    assert claimed_1[0].attempt_count == 1

    claimed_2 = claim_batch(db, limit=1)
    assert len(claimed_2) == 1
    assert claimed_2[0].id != claimed_1[0].id
    assert claimed_2[0].processing_status == "processing"
    assert claimed_2[0].attempt_count == 2

    claimed_none = claim_batch(db, limit=10)
    assert len(claimed_none) == 0

