# Background Workers & Outbox Sweeper Operational Runbook

**Date**: November 4, 2026  
**Audience**: DevOps, SREs, Backend Engineers, and System Operators  
**Component**: Asynchronous Outbox Sweeper & Integration Retry Worker (`backend/scripts/switch_retry.py`)

---

## 1. Architecture & Concurrency Model

### 1.1 The Outbox Delivery Problem
SceneSteward avoids dual-write inconsistencies (e.g. updating PostgreSQL while concurrently sending an HTTP request to Switch or Claude) by adopting the **Transactional Outbox Pattern**.
- Domain changes and outbox records (`integration_events`) are committed inside a single database transaction.
- Outbound delivery to external systems is performed asynchronously by background sweeper workers.

### 1.2 Multi-Worker Safe Atomic Claim
To allow multiple worker replicas to run concurrently without race conditions or duplicate deliveries, the sweeper uses PostgreSQL's native row-level lock skipping:
```python
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
```
- Rows already locked by another worker instance are skipped immediately (`SKIP LOCKED`), preventing deadlocks.
- The state transition from `failed` to `processing` occurs inside an atomic atomic statement with incremented `attempt_count`.

---

## 2. Retry Policy & Dead-Letter Handling

1. **Attempt Limits**:
   - `MAX_ATTEMPTS = 3`.
2. **Dead-Letter Escalation**:
   - If delivery fails after 3 attempts or if the event payload has an invalid reference:
     - `processing_status` is updated to `dead_letter`.
     - An immutable incident record is created via `notify_integration_failure()`.
     - A human task is generated in `switch_tasks` assigned to the project owner/care lead.

---

## 3. Operator Procedures

### 3.1 Inspecting Failed & Dead-Letter Events
Run the following query as `scenesteward_readonly` or via an operational psql session:
```sql
SELECT id, project_id, integration_name, processing_status, attempt_count, last_error, created_at
FROM integration_events
WHERE processing_status IN ('failed', 'dead_letter')
ORDER BY created_at DESC
LIMIT 50;
```

### 3.2 Requeuing Dead-Letter Events
Once the downstream external service (e.g. Switch Core or network connectivity) is restored, an operator can requeue parked dead-letter events for re-processing:
```sql
UPDATE integration_events
SET processing_status = 'failed',
    attempt_count = 0,
    last_error = NULL
WHERE processing_status = 'dead_letter'
  AND integration_name = 'switch';
```

### 3.3 Worker Process Management
- **Cron / Periodic Execution**:
  ```bash
  # Run every 2 minutes
  */2 * * * * cd /opt/scenesteward/backend && ./.venv/bin/python scripts/switch_retry.py >> /var/log/scenesteward/switch_retry.log 2>&1
  ```
- **Systemd Service**:
  When deployed as a continuous background daemon, configure `Restart=on-failure` and `RestartSec=5s` in the systemd unit file.
- **Graceful Shutdown**:
  Workers handle `SIGTERM` and `SIGINT` by finishing the active single event before exiting.

