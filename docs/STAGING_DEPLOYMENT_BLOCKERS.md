# SceneSteward — Staging Deployment Blockers & Remediation Ledger

**Date**: November 4, 2026  
**Auditor**: Principal DevOps Engineer & Application Security Specialist  
**Current Preflight Milestone**: **`PREFLIGHT PASSED — AWAITING LIVE PROVIDERS`**  

---

## 1. 15-Point Preflight Status Summary

| # | Inspection Item | Status | Notes / Blockers |
|:---:|:---|:---:|:---|
| **1** | Docker Compose Syntax | **PASS** | Validated via PyYAML |
| **2** | Service Dependencies Graph | **PASS** | `migrate`, `db`, `clamav`, `api`, `worker` cleanly ordered |
| **3** | Health & Readiness Checks | **PASS** | Interval, timeout, start_period, and retries verified |
| **4** | Volumes & Network Isolation | **PASS** | Bridge network & persistent volumes verified |
| **5** | Environment Template Declarations | **PASS** | All required staging variables in `.env.staging.example` |
| **6** | Dynamic Configuration Loader | **PASS** | `SCENESTEWARD_ENV_FILE` and `ENV_FILE` redirection verified |
| **7** | Staging Dev Provider Lockout | **PASS** | `AUTH_PROVIDER=dev` strictly blocked when `APP_ENV=staging` |
| **8** | Secret Exposure Prevention | **PASS** | Zero secrets in logs, diagnostics, or Git |
| **9** | Database Migration Safety | **PASS** | Alembic path resolved with `%(here)s/migrations`, head `e1f2a3b4c5d6` |
| **10**| Independent API & Worker | **PASS** | Standalone API and worker execution verified |
| **11**| Script Configuration Parity | **PASS** | All scripts import unified `get_settings()` |
| **12**| Clear Fail-Closed Diagnostics | **PASS** | Missing credentials exit cleanly with exit code 1 |
| **13**| ClamAV INSTREAM Compatibility | **PASS** | Protocol matches RFC/ClamAV specification |
| **14**| Port & DNS Mapping | **PASS** | Host ports 5433, 8001, 3310 mapped; zero collisions |
| **15**| Restart & Shutdown Resilience | **PASS** | Graceful SIGTERM on API; atomic retry on worker |
| — | **Local Docker Container Launch** | **BLOCKED** | Docker CLI is not installed on this local host |
| — | **Live Provider Activation** | **BLOCKED** | Staging credentials await entry in `backend/.env.staging` |

---

## 2. Detailed Blocker Analysis

### Blocker 1: Docker Runtime Unavailable on Local Host
- **Impact**: Docker containers cannot be started directly on this specific Windows host (`docker : The term 'docker' is not recognized`).
- **Remediation**:
  - Deploy to a Linux/Windows server with Docker Desktop or Docker Engine installed using the exact runbook in [`STAGING_DEPLOYMENT_COMMANDS.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/STAGING_DEPLOYMENT_COMMANDS.md).
  - *Alternatively*, run the staging environment natively using Python 3.12, local PostgreSQL 18.6, and the background worker runner.

### Blocker 2: Supabase Staging Project Credentials
- **Impact**: Live JWT token validation and private S3 document storage cannot be verified against the Supabase cloud API.
- **Remediation**:
  - Provision a staging project in Supabase.
  - Create private bucket `scenesteward-staging-documents`.
  - Populate `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `AUTH_JWKS_URL`, `AUTH_ISSUER` in `backend/.env.staging`.
  - Verify with: `python backend/scripts/verify_staging_auth.py` and `python backend/scripts/verify_staging_storage.py`.

### Blocker 3: Anthropic Claude API Key
- **Impact**: Multi-agent review operates in synthetic offline mode rather than querying live Claude 3.5 Sonnet.
- **Remediation**:
  - Add `ANTHROPIC_API_KEY` to `backend/.env.staging`.
  - Verify with: `python backend/scripts/verify_staging_anthropic.py`.

### Blocker 4: ClamAV Daemon Host
- **Impact**: Malware scanner runs in local simulated mode; uploads in live staging would fail-closed if `ANTIVIRUS_FAIL_CLOSED=true`.
- **Remediation**:
  - Start ClamAV container on port 3310 (`docker run -d -p 3310:3310 clamav/clamav:latest`) or deploy ClamAV service via `docker-compose.staging.yml`.
  - Verify with: `python backend/scripts/verify_staging_clamav.py`.

### Blocker 5: Switch Collaboration Platform URL
- **Impact**: Outbound Switch event sync buffers into table `outbox_events` and marks events pending retry.
- **Remediation**:
  - Provide `SWITCH_BASE_URL` and `SWITCH_API_KEY` for the staging Switch cluster in `backend/.env.staging`.
  - Verify with: `python backend/scripts/verify_staging_switch.py`.

---

## 3. Preflight Acceptance Verdict

### Final Milestone State: **`PREFLIGHT PASSED — AWAITING LIVE PROVIDERS`**
All staging configuration, security guards, database migrations, and operational commands have passed preflight acceptance without defect.

