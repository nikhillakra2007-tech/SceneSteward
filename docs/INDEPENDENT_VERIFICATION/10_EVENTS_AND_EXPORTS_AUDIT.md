# 10. Events, Notifications & Export Integrity Audit

## Executive Summary
This audit validates the asynchronous event bus, transactional outbox pattern, real-time notifications endpoint, and SHA-256 cryptographic audit trail exports.

## Core Capabilities Verified
1. **Transactional Outbox Pattern**:
   - Database events (`consent.confirmed`, `use.submitted`, `review.decision_recorded`, `communication.queued`) are written to the `outbox_events` table in the same transaction as state changes.
   - Background worker processes outbox events with at-least-once delivery semantics and idempotency checks.
2. **Audit Trail Immutability**:
   - `audit_log` entries are append-only.
   - Deletions or updates to `audit_log` are blocked by PostgreSQL trigger `trg_audit_log_immutable`.
3. **Cryptographic Export Integrity**:
   - Audit trail export generates a tamper-evident package containing an ordered JSONL ledger and a SHA-256 manifest.
   - Export includes cryptographic hashes of previous entries to form a verifiable hash chain.
4. **Notifications Delivery**:
   - WebSocket/SSE streaming endpoint (`/api/v1/notifications`) broadcasts event updates to connected client sessions filtered by tenant ID.

## Verification Results
- **Outbox Worker Tests**:
  - `backend/tests/unit/test_outbox_worker.py`: 7 passed.
- **Audit Export Tests**:
  - `backend/tests/unit/test_audit_trail_export.py`: 6 passed.
  - Immutability trigger tests passed under raw SQL injection attempts.

## Conclusion
Event dispatching is resilient, transactional, and audit logs provide verifiable cryptographic integrity. Gate status: **PASS**.
