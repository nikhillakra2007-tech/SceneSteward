# SceneSteward — Production Recovery Runbook

**Document Version:** 1.0.0  
**Effective Date:** 2026-11-06  
**Audience:** Site Reliability Engineers, On-Call DevSecOps, Production Operations  

---

## 1. Incident Classification & Severity

| Severity Level | Criteria | Target Response | Target Resolution |
|---|---|---|---|
| **SEV-1 (Critical)** | Core API down, database inaccessible, data corruption suspected, or RLS security boundary breach. | < 15 minutes | < 2 hours |
| **SEV-2 (High)** | ClamAV scanner unavailable (uploads blocked fail-closed), Redis down (falling back to in-memory), or worker failing. | < 30 minutes | < 4 hours |
| **SEV-3 (Medium)** | Degraded API performance, single provider webhook failure, non-fatal rate limiting alerts. | < 2 hours | < 1 business day |

---

## 2. Emergency Disaster Scenarios & Immediate Actions

### 2.1 Database Unavailability / Connection Exhaustion
**Symptoms:** `/health/ready` returns HTTP 503; logs show `OperationalError: connection refused` or `too many clients`.

**Action Steps:**
1. Check database container status:
   ```bash
   docker compose -f docker-compose.prod.yml ps db
   docker compose -f docker-compose.prod.yml logs --tail 100 db
   ```
2. Verify active connections:
   ```bash
   docker exec -it scenesteward-prod-db psql -U scenesteward_prod -c \
     "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
   ```
3. If connections are orphaned by an unhealthy pool:
   ```bash
   docker exec -it scenesteward-prod-db psql -U scenesteward_prod -c \
     "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - INTERVAL '5 minutes';"
   ```
4. If database process crashed:
   ```bash
   docker compose -f docker-compose.prod.yml restart db
   ```

### 2.2 ClamAV Daemon Crash (File Uploads Failing Fail-Closed)
**Symptoms:** File uploads return HTTP 503 `Antivirus scanner is unavailable`. `/health/ready` shows `antivirus: { status: "error" }`.

**Action Steps:**
1. Check ClamAV container logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail 50 clamav
   ```
2. Test daemon socket connectivity:
   ```bash
   docker exec -it scenesteward-prod-api python -c \
     "from app.services.malware_scanner import ping_clamav; print(ping_clamav('clamav', 3310))"
   ```
3. Restart daemon if memory exhausted:
   ```bash
   docker compose -f docker-compose.prod.yml restart clamav
   ```

### 2.3 Worker Egress Loop Stalled
**Symptoms:** Outbound Switch webhook events remain in `pending` status past retry backoff windows.

**Action Steps:**
1. Inspect worker health probe:
   ```bash
   docker exec -it scenesteward-prod-worker python scripts/switch_retry.py --check-health
   ```
2. Run single retry sweep to inspect error output:
   ```bash
   docker exec -it scenesteward-prod-worker python scripts/switch_retry.py --once
   ```
3. Restart worker container:
   ```bash
   docker compose -f docker-compose.prod.yml restart worker
   ```

---

## 3. Routine Health Probing & Verification

- **Liveness Probe:** `GET /health` or `GET /health/live` (Expects HTTP 200).
- **Readiness Probe:** `GET /health/ready` (Expects HTTP 200; checks DB, Redis, ClamAV).
- **Integration Status:** `GET /api/v1/integrations/status` (Provides detailed service breakdown).
- **Automated Lifecycle Script:**
  ```bash
  python backend/scripts/verify_documentary_lifecycle.py
  ```

