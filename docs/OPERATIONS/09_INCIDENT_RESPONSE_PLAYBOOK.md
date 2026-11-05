# SceneSteward Runbook 09: Incident Response Playbook

**Document ID:** `RB-09-INCIDENT-RESPONSE`  
**Target Environment:** All Environments  
**Audience:** On-Call Engineers, Incident Commanders  

---

## 1. Incident Classification

| Severity | Definition | Target Response | Notification Channel |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Core API unavailable, database trust handshake failure, data loss risk | < 15 minutes | PagerDuty, War Room |
| **SEV-2 (Major)** | ClamAV scanner down in fail-closed mode (uploads blocked), rate limiting offline | < 30 minutes | PagerDuty, Slack #ops-alerts |
| **SEV-3 (Minor)** | Switch background worker delayed, AI extraction latency elevated | < 2 hours | Slack #ops-alerts |
| **SEV-4 (Low)** | Non-blocking metric ingestion issues, minor UI glitches | Next business day | Jira / Linear |

---

## 2. Triage & Diagnosis Workflow

### Step 1: Query API Health Probe
```bash
curl -s http://127.0.0.1:8000/health/ready | jq .
```
- If HTTP 503 and `checks.database.status: "error"` -> **Database Failure**.
- If HTTP 503 and `checks.clamav.status: "error"` -> **ClamAV Scanner Failure**.
- If HTTP 200 and `status: "degraded"` -> **Non-critical component offline (e.g. Redis)**.

### Step 2: Inspect Container Status and Logs
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 api
docker compose -f docker-compose.prod.yml logs --tail=100 db
```

### Step 3: Check Trust Handshake Status
If API is failing to boot with:
`FATAL DATABASE TRUST FAILURE: Application secret does not match PostgreSQL RLS trust boundary`
Follow `RB-05-SECRET-MANAGEMENT` to reconcile `DATABASE_IDENTITY_SECRET` between `.env.production` and `private.app_secrets`.

---

## 3. Post-Incident Review (PIR)
Within 48 hours of any SEV-1 or SEV-2 incident:
1. Conduct blameless retrospective.
2. Produce root-cause analysis (RCA) document.
3. Track remediation action items with issue numbers.
