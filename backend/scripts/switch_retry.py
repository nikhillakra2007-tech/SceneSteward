"""Bounded retry sweeper for failed Switch deliveries.

Retries integration_events(integration_name='switch', processing_status='failed',
attempt_count < 3). Events are only re-sent for review-context deliveries with a
parseable proposed_use reference; unparseable events go straight to dead_letter.
After the 3rd failed attempt the event is parked as dead_letter and an
integration_failure task is created for a human.

Usage:  python scripts/switch_retry.py
Exit code 0 = sweep completed (regardless of individual failures).
"""
from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import get_session_factory
from app.integrations.switch import get_switch_adapter, switch_status
from app.models import IntegrationEvent, ProposedUse, SwitchRoomLink
from app.services import tasks

MAX_ATTEMPTS = 3


def main() -> int:
    session = get_session_factory()()
    retried = sent = parked = 0
    try:
        status = switch_status()
        if status.status != "configured_verified":
            print(f"Switch not verified ({status.status}); no deliveries attempted.")
            return 0

        adapter = get_switch_adapter()
        events = (
            session.query(IntegrationEvent)
            .filter(IntegrationEvent.integration_name == "switch",
                    IntegrationEvent.processing_status == "failed",
                    IntegrationEvent.attempt_count < MAX_ATTEMPTS)
            .order_by(IntegrationEvent.created_at.asc())
            .limit(100)
            .all()
        )
        for evt in events:
            ref = evt.payload_reference or ""
            if not ref.startswith("proposed_use:"):
                evt.processing_status = "dead_letter"
                evt.last_error = (evt.last_error or "") + " | unparseable reference parked"
                parked += 1
                continue
            use = session.get(ProposedUse, uuid.UUID(ref.split(":", 1)[1]))
            if use is None:
                evt.processing_status = "dead_letter"
                evt.last_error = "proposed_use no longer exists"
                parked += 1
                continue

            link = (
                session.query(SwitchRoomLink)
                .filter(SwitchRoomLink.project_id == use.project_id,
                        SwitchRoomLink.participant_id == use.participant_id)
                .order_by(SwitchRoomLink.room_type.desc())  # participant_review first
                .first()
            ) or session.query(SwitchRoomLink).filter(SwitchRoomLink.project_id == use.project_id).first()

            evt.attempt_count += 1
            if link is None:
                evt.last_error = "no switch room linked"
                if evt.attempt_count >= MAX_ATTEMPTS:
                    evt.processing_status = "dead_letter"
                    parked += 1
                continue

            summary = {"proposed_use_id": str(use.id),
                       "outcome": (evt.payload_summary or {}).get("outcome", "UNKNOWN"),
                       "missing_categories": [], "declined_categories": []}
            send = adapter.send_review_context(room_id=link.switch_room_id, summary=summary,
                                               correlation_id=str(evt.correlation_id))
            if send.ok:
                evt.processing_status = "processed"
                evt.processed_at = datetime.now(UTC)
                evt.last_error = None
                sent += 1
            else:
                evt.last_error = send.error_code or "send_failed"
                if evt.attempt_count >= MAX_ATTEMPTS:
                    evt.processing_status = "dead_letter"
                    parked += 1
                    tasks.create_task(
                        session, project_id=use.project_id, participant_id=use.participant_id,
                        task_type="integration_failure",
                        title="Switch delivery permanently failed",
                        description=f"correlation_id={evt.correlation_id} error={evt.last_error}",
                        priority="high", source_type="integration_event", source_id=evt.id,
                        created_by_actor_type="integration",
                    )
            retried += 1

        session.commit()
        print(f"sweep complete: candidates={len(events)} retried={retried} delivered={sent} parked={parked}")
        return 0
    except Exception as exc:  # noqa: BLE001 — the sweep reports and exits non-zero; individual events were already handled
        session.rollback()
        print(f"sweep failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
