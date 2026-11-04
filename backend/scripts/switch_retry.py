"""Bounded, multi-worker-safe retry sweeper for failed Switch deliveries.

Atomic claim: each candidate row is moved failed → processing in a single
UPDATE ... WHERE id=? AND status='failed' statement. Two concurrent workers can
never both process the same event (the loser's UPDATE matches zero rows).

Unparseable events go to dead_letter. After MAX_ATTEMPTS failed deliveries the
event is parked as dead_letter and a human-owned integration_failure task is
created via the notification sink.

Usage:  python scripts/switch_retry.py
Exit code 0 = sweep completed (regardless of individual failures).
"""
from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, update

from app.core.database import get_session_factory, system_context
from app.integrations.switch import get_switch_adapter, switch_status
from app.models import IntegrationEvent, ProposedUse, SwitchRoomLink

MAX_ATTEMPTS = 3


def claim_batch(session, limit: int = 100) -> list[IntegrationEvent]:
    """Atomically claim up to `limit` failed events for this worker using FOR UPDATE SKIP LOCKED."""
    subq = (
        select(IntegrationEvent.id)
        .where(
            IntegrationEvent.integration_name == "switch",
            IntegrationEvent.processing_status == "failed",
            IntegrationEvent.attempt_count < MAX_ATTEMPTS,
        )
        .order_by(IntegrationEvent.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    stmt = (
        update(IntegrationEvent)
        .where(IntegrationEvent.id.in_(subq))
        .values(
            processing_status="processing",
            attempt_count=IntegrationEvent.attempt_count + 1,
        )
        .returning(IntegrationEvent.id)
    )
    claimed_ids = session.scalars(stmt).all()
    if not claimed_ids:
        session.commit()
        return []

    claimed = session.execute(
        select(IntegrationEvent).where(IntegrationEvent.id.in_(claimed_ids))
    ).scalars().all()
    session.commit()
    return list(claimed)


def main() -> int:
    session = get_session_factory()()
    retried = sent = parked = 0
    try:
        with system_context(session):
            status = switch_status()
            if status.status != "configured_verified":
                print(f"Switch not verified ({status.status}); no deliveries attempted.")
                return 0

            adapter = get_switch_adapter()
            for evt in claim_batch(session):
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

                if link is None:
                    evt.last_error = "no switch room linked"
                    if evt.attempt_count >= MAX_ATTEMPTS:
                        evt.processing_status = "dead_letter"
                        parked += 1
                        from app.integrations.notifications import notify_integration_failure
                        notify_integration_failure(
                            session, project_id=use.project_id, participant_id=use.participant_id,
                            title="Switch delivery permanently failed (no room linked)",
                            detail=f"correlation_id={evt.correlation_id}",
                            correlation_id=evt.correlation_id,
                        )
                    else:
                        evt.processing_status = "failed"
                    continue

                summary = {"proposed_use_id": str(use.id),
                           "outcome": (evt.payload_summary or {}).get("outcome", "UNKNOWN"),
                           "missing_categories": [], "declined_categories": []}
                try:
                    send = adapter.send_review_context(room_id=link.switch_room_id, summary=summary,
                                                       correlation_id=str(evt.correlation_id))
                except Exception as send_exc:  # noqa: BLE001 — never let one event kill the sweep
                    send = type("SendResult", (), {"ok": False, "error_code": f"exception:{type(send_exc).__name__}"})()

                if send.ok:
                    evt.processing_status = "processed"
                    evt.processed_at = datetime.now(UTC)
                    evt.last_error = None
                    sent += 1
                else:
                    evt.last_error = getattr(send, "error_code", None) or "send_failed"
                    if evt.attempt_count >= MAX_ATTEMPTS:
                        evt.processing_status = "dead_letter"
                        parked += 1
                        from app.integrations.notifications import notify_integration_failure
                        notify_integration_failure(
                            session, project_id=use.project_id, participant_id=use.participant_id,
                            title="Switch delivery permanently failed",
                            detail=f"correlation_id={evt.correlation_id} error={evt.last_error}",
                            correlation_id=evt.correlation_id,
                        )
                    else:
                        evt.processing_status = "failed"  # back to the queue, retry next sweep
                retried += 1

            session.commit()
        print(f"sweep complete: retried={retried} delivered={sent} parked={parked}")
        return 0
    except Exception as exc:  # noqa: BLE001 — the sweep reports and exits non-zero
        session.rollback()
        print(f"sweep failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    if "--loop" in sys.argv or "--daemon" in sys.argv:
        import time
        print("Starting switch_retry daemon loop (interval 10s)...")
        while True:
            try:
                main()
            except Exception as e:  # noqa: BLE001
                print(f"Error in daemon loop: {e}", file=sys.stderr)
            time.sleep(10)
    else:
        raise SystemExit(main())
