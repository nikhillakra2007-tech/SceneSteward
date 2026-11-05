# SceneSteward Runbook 16: Switch Outbox Worker Operations

**Document ID:** `RB-16-SWITCH-WORKER`  
**Target Environment:** Staging, Production  
**Audience:** SREs, Integration Engineers  

---

## 1. Outbox Worker Architecture
The background worker (`scripts/switch_retry.py --loop`) processes asynchronous events destined for external collaborator systems (Agent Switch):
1. Events are written atomically into table `switch_outbox` during the primary database transaction (guaranteeing consistency).
2. The worker polls pending records with `status = 'pending'` or `status = 'retrying'`.
3. Delivery attempts execute with exponential backoff and jitter.
4. Messages that exceed maximum retry thresholds transition to `status = 'dead_letter'`.

---

## 2. Inspecting Outbox Status
Connect to PostgreSQL and query outbox metrics:
```sql
SELECT status, count(*) 
FROM switch_outbox 
GROUP BY status;
```

Inspect failing messages:
```sql
SELECT id, event_type, attempts, last_error, next_retry_at 
FROM switch_outbox 
WHERE status = 'retrying' 
ORDER BY next_retry_at ASC 
LIMIT 10;
```

---

## 3. Re-driving Dead-Letter Messages
To re-queue messages that encountered transient external failures:
```sql
UPDATE switch_outbox 
SET status = 'pending', attempts = 0, next_retry_at = now() 
WHERE status = 'dead_letter' AND created_at > now() - interval '24 hours';
```

Restart the worker process if stuck:
```bash
docker compose -f docker-compose.prod.yml restart worker
```
