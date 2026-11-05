# SceneSteward Runbook 09: Incident Response Playbook

**Document ID:** `RB-09-INCIDENT-RESPONSE`  
**Target Environment:** All Environments  
**Audience:** On-Call Engineers, Incident Commanders, SREs  
**Last Updated:** 2026-11-06  

---

## 1. Incident Classification Matrix

| Severity | Definition | Target MTTR | Notification Channel | Escalation Path |
| :--- | :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Core API unavailable (HTTP 503), database trust handshake failure, runtime role least-privilege violation, data loss risk | < 15 min | PagerDuty, War Room | SRE Lead + Security Architect |
| **SEV-2 (Major)** | ClamAV daemon down (fail-closed uploads blocked), production Redis rate limiter failure (HTTP 503), unmigrated database startup | < 30 min | PagerDuty, Slack #ops-alerts | Tech Lead |
| **SEV-3 (Minor)** | Switch background worker heartbeat stale (> 30s), delivery retries backing up, non-blocking latency | < 2 hours | Slack #ops-alerts | On-Call Engineer |
| **SEV-4 (Low)** | Minor UI telemetry glitch, non-blocking non-customer-facing metric lag | Next business day | Linear / Jira | Product Engineering |

---

## 2. Rapid Triage & Diagnostic Workflows

### Step 1: Query API Health Probe
```bash
curl -s http://127.0.0.1:8000/health/ready | jq .
```
- **HTTP 503 and `checks.database.status: "error"`**: Database connection down or unreachable.
- **HTTP 503 and `checks.database.status: "unmigrated"`**: Database missing migration version table or unmigrated; trigger `docker compose run --rm migrate`.
- **HTTP 503 and `checks.redis.status: "error"`**: In production, Redis failure fails closed to preserve rate-limiting boundaries.
- **HTTP 503 and `checks.clamav.status: "error"`**: In fail-closed mode (`ANTIVIRUS_FAIL_CLOSED=true`), document uploads are safely gated.
- **HTTP 200 and `status: "degraded"`**: Non-production environment operating with graceful degradation.

### Step 2: Inspect Worker Health & Heartbeat
```bash
# Query the containerized worker health probe
docker compose -f docker-compose.prod.yml exec worker python scripts/switch_retry.py --check-health

# Check worker heartbeat JSON directly
cat backend/var/worker_heartbeat.json | jq .
```
- If exit code 1 or heartbeat is > 30 seconds old, inspect worker logs for stalled transactions or external adapter timeouts:
```bash
docker compose -f docker-compose.prod.yml logs --tail=100 worker
```
- The worker automatically executes `recover_stale_events()` on each cycle to reclaim events orphaned by process termination.

### Step 3: Check Least-Privilege Role Separation
If application logs report:
`FATAL SECURITY CONFIGURATION: Application is running as superuser or role with BYPASSRLS privilege in production`
The application was connected via the schema owner role (`scenesteward_prod`) instead of `scenesteward_app`.
- Immediately update `DATABASE_URL` in `backend/.env.production` to point to `scenesteward_app`.
- Ensure `MIGRATION_DATABASE_URL` points to `scenesteward_prod`.

### Step 4: Check Trust Handshake Status
If API fails to boot with:
`FATAL DATABASE TRUST FAILURE: Application secret does not match PostgreSQL RLS trust boundary`
Follow `RB-05-SECRET-MANAGEMENT` to reconcile `DATABASE_IDENTITY_SECRET` between `.env.production` and PostgreSQL `private.app_secrets`.

---

## 3. Post-Incident Review (PIR)
Within 48 hours of any SEV-1 or SEV-2 incident:
1. Conduct a blameless post-incident retrospective.
2. Publish root-cause analysis (RCA) covering timeline, detection gap, and contributing factors.
3. Track remediation and prevention issues with assigned owners.
