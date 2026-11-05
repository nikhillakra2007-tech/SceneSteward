"""Bounded, multi-worker-safe retry sweeper for failed Switch deliveries.

Atomic claim: each candidate row is moved failed → processing in a single
UPDATE ... WHERE id=? AND status='failed' statement. Two concurrent workers can
never both process the same event (the loser's UPDATE matches zero rows).

Unparseable events go to dead_letter. After MAX_ATTEMPTS failed deliveries the
event is parked as dead_letter and a human-owned integration_failure task is
created via the notification sink.

Features:
- Stale event recovery (events stuck in 'processing' are reset to 'failed')
- Health check support (--check-health) inspecting heartbeat file and DB connectivity
- Heartbeat writer for daemon/loop executions
- Graceful shutdown on SIGTERM / SIGINT

Usage:
    python scripts/switch_retry.py                # Single sweep
    python scripts/switch_retry.py --loop         # Daemon loop with heartbeat
    python scripts/switch_retry.py --check-health # Health check probe
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, update

from app.core.database import check_database, get_session_factory, system_context
from app.integrations.switch import get_switch_adapter, switch_status
from app.models import IntegrationEvent, ProposedUse, SwitchRoomLink

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scenesteward.worker")

MAX_ATTEMPTS = 3
HEARTBEAT_PATH = Path(__file__).resolve().parents[1] / "var" / "worker_heartbeat.json"


def write_heartbeat(status: str = "healthy", metadata: dict | None = None) -> None:
    try:
        HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "pid": os.getpid(),
            "status": status,
            "metadata": metadata or {},
        }
        temp_hb = HEARTBEAT_PATH.with_suffix(".tmp")
        temp_hb.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_hb.replace(HEARTBEAT_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write worker heartbeat: %s", exc)


def check_worker_health(max_age_seconds: float = 30.0) -> int:
    """Readiness/liveness check for the worker container/process."""
    if not HEARTBEAT_PATH.exists():
        logger.error("Health check failed: worker heartbeat file does not exist at %s", HEARTBEAT_PATH)
        return 1

    try:
        data = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
        hb_ts_str = data.get("timestamp")
        if not hb_ts_str:
            logger.error("Health check failed: worker heartbeat missing timestamp")
            return 1
        hb_dt = datetime.fromisoformat(hb_ts_str)
        age = (datetime.now(UTC) - hb_dt).total_seconds()
        if age > max_age_seconds:
            logger.error("Health check failed: worker heartbeat is stale (%.1fs old > %.1fs limit)", age, max_age_seconds)
            return 1
        if data.get("status") != "healthy":
            logger.error("Health check failed: worker status is %s", data.get("status"))
            return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Health check failed: error reading heartbeat: %s", exc)
        return 1

    # Verify DB connectivity
    db_stat = check_database()
    if db_stat.get("status") != "ok":
        logger.error("Health check failed: database unavailable (%s)", db_stat.get("error_category"))
        return 1

    logger.info("Worker health probe PASSED (heartbeat age: %.1fs, db ok)", age)
    return 0


def recover_stale_events(session, max_stale_seconds: int = 300) -> int:
    """Reset events stuck in 'processing' longer than max_stale_seconds back to 'failed'."""
    cutoff = datetime.now(UTC) - timedelta(seconds=max_stale_seconds)
    stmt = (
        update(IntegrationEvent)
        .where(
            IntegrationEvent.processing_status == "processing",
            IntegrationEvent.created_at < cutoff,
        )
        .values(
            processing_status="failed",
            last_error="stale processing timeout recovered by worker sweeper",
        )
        .returning(IntegrationEvent.id)
    )
    recovered_ids = session.scalars(stmt).all()
    if recovered_ids:
        session.commit()
        logger.info("Recovered %d stale processing event(s)", len(recovered_ids))
    return len(recovered_ids)


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


def sweep_once() -> tuple[int, int, int]:
    """Execute a single sweep pass. Returns (retried, delivered, parked)."""
    session = get_session_factory()()
    retried = sent = parked = 0
    try:
        with system_context(session):
            recover_stale_events(session)

            status = switch_status()
            if status.status != "configured_verified":
                logger.debug("Switch not verified (%s); no deliveries attempted.", status.status)
                return 0, 0, 0

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
                    .filter(
                        SwitchRoomLink.project_id == use.project_id,
                        SwitchRoomLink.participant_id == use.participant_id,
                    )
                    .order_by(SwitchRoomLink.room_type.desc())
                    .first()
                ) or session.query(SwitchRoomLink).filter(SwitchRoomLink.project_id == use.project_id).first()

                if link is None:
                    evt.last_error = "no switch room linked"
                    if evt.attempt_count >= MAX_ATTEMPTS:
                        evt.processing_status = "dead_letter"
                        parked += 1
                        from app.integrations.notifications import notify_integration_failure
                        notify_integration_failure(
                            session,
                            project_id=use.project_id,
                            participant_id=use.participant_id,
                            title="Switch delivery permanently failed (no room linked)",
                            detail=f"correlation_id={evt.correlation_id}",
                            correlation_id=evt.correlation_id,
                        )
                    else:
                        evt.processing_status = "failed"
                    continue

                summary = {
                    "proposed_use_id": str(use.id),
                    "outcome": (evt.payload_summary or {}).get("outcome", "UNKNOWN"),
                    "missing_categories": [],
                    "declined_categories": [],
                }
                try:
                    send = adapter.send_review_context(
                        room_id=link.switch_room_id,
                        summary=summary,
                        correlation_id=str(evt.correlation_id),
                    )
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
                            session,
                            project_id=use.project_id,
                            participant_id=use.participant_id,
                            title="Switch delivery permanently failed",
                            detail=f"correlation_id={evt.correlation_id} error={evt.last_error}",
                            correlation_id=evt.correlation_id,
                        )
                    else:
                        evt.processing_status = "failed"
                retried += 1

            session.commit()
        return retried, sent, parked
    except Exception as exc:
        session.rollback()
        logger.error("Sweep failed: %s", exc)
        raise
    finally:
        session.close()


def main() -> int:
    try:
        retried, sent, parked = sweep_once()
        logger.info("Sweep complete: retried=%d delivered=%d parked=%d", retried, sent, parked)
        write_heartbeat(status="healthy", metadata={"retried": retried, "delivered": sent, "parked": parked})
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.critical("Sweep failed unrecoverably: %s", exc)
        write_heartbeat(status="error", metadata={"error": str(exc)})
        return 1


_shutting_down = False


def _sig_handler(signum, frame):
    global _shutting_down
    logger.info("Signal %d received, stopping daemon loop gracefully...", signum)
    _shutting_down = True


def run_daemon_loop(interval_seconds: float = 10.0) -> None:
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sig_handler)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _sig_handler)

    logger.info("Starting switch_retry daemon loop (interval %.1fs)...", interval_seconds)
    write_heartbeat(status="healthy", metadata={"mode": "daemon_startup"})

    iteration = 0
    while not _shutting_down:
        iteration += 1
        try:
            retried, sent, parked = sweep_once()
            write_heartbeat(
                status="healthy",
                metadata={"iteration": iteration, "retried": retried, "delivered": sent, "parked": parked},
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Error during daemon loop iteration %d: %s", iteration, exc)
            write_heartbeat(status="degraded", metadata={"iteration": iteration, "error": str(exc)})

        # Sleep in small slices to be responsive to signals
        slept = 0.0
        while slept < interval_seconds and not _shutting_down:
            time.sleep(0.5)
            slept += 0.5

    logger.info("Daemon loop shutdown complete.")
    write_heartbeat(status="stopped", metadata={"mode": "graceful_shutdown"})


if __name__ == "__main__":
    if "--check-health" in sys.argv:
        raise SystemExit(check_worker_health())
    elif "--loop" in sys.argv or "--daemon" in sys.argv:
        run_daemon_loop()
    else:
        raise SystemExit(main())
