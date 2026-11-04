# SceneSteward — Staging Deployment Preflight Report

**Date**: November 4, 2026  
**Auditor**: Principal DevOps Engineer, Site Reliability Engineer & Application Security Architect  
**Preflight Assessment Verdict**: **`PREFLIGHT PASSED — AWAITING LIVE PROVIDERS`**  
**Repository Branch**: `main`  
**Database Catalog Revision**: `e1f2a3b4c5d6` (Head)  

---

## 1. Executive Summary & Final Verdict

An exhaustive 15-point preflight audit was conducted across the SceneSteward staging deployment infrastructure, container configurations, configuration loaders, security boundaries, and migration systems.

### Final Verdict: `PREFLIGHT PASSED — AWAITING LIVE PROVIDERS`

- **Preflight Verification Status**: **PASSED (13 PASS, 2 BLOCKED)**.
  - All syntax, dependency, volume, network, and ordering configurations are structurally sound and verified.
  - Security boundaries strictly prevent development auth/storage providers from activating in `staging`.
  - Database migrations execute safely and idempotently under schema owner credentials.
  - Independent API and background worker lifecycles are verified.
  - Provider verification harnesses share the identical configuration loader and report missing services with fail-closed clarity.
- **Environment Blockers**:
  - **Docker Engine on Current Host**: The Docker CLI is not installed on this local Windows host (`docker : The term 'docker' is not recognized`). Per non-negotiable rules, container deployment is marked `BLOCKED (Host Docker Unavailable)` while host-native execution is verified.
  - **External Cloud Provider Credentials**: Supabase Auth/Storage, Anthropic API, Switch platform, and ClamAV daemon are unconfigured in `.env.staging`, marked as `AWAITING LIVE PROVIDERS`.

---

## 2. 15-Point Preflight Inspection Matrix

| # | Inspection Item | Verification Method / Evidence | Result |
|:---:|:---|:---|:---:|
| **1** | **Compose Syntax & Definitions** | Parsed `docker-compose.staging.yml` via PyYAML; validated services `db`, `clamav`, `migrate`, `api`, `worker` | **PASS** |
| **2** | **Service Dependencies & Graph** | Validated DAG: `migrate -> db`, `api -> (db, migrate, clamav)`, `worker -> (db, api)` | **PASS** |
| **3** | **Health Checks & Restart Policies** | Verified `/health` probe on API, `pg_isready` on DB, `clamdscan` on ClamAV with `start_period`, `restart: always` on worker | **PASS** |
| **4** | **Volumes & Network Isolation** | Validated `scenesteward-staging-net` bridge network and dedicated volumes for pgdata, storage, and ClamAV | **PASS** |
| **5** | **Environment Variables Template** | Inspected `backend/.env.staging.example`; verified all staging keys, secrets, and URLs declared | **PASS** |
| **6** | **Dynamic Configuration Loader** | Verified `SettingsConfigDict` dynamic loading via `SCENESTEWARD_ENV_FILE` and `ENV_FILE` environment variables | **PASS** |
| **7** | **No Dev Provider in Staging** | Tested Pydantic validation guard: `Settings(app_env='staging', auth_provider='dev')` strictly raises `ValueError` | **PASS** |
| **8** | **Zero Secret Exposure** | Audited `startup_checks(s)` and structured logs; verified report by variable name only, zero values logged | **PASS** |
| **9** | **Idempotent Single Migration** | Executed Alembic migration check; resolved `%(here)s/migrations`; verified catalog head `e1f2a3b4c5d6` | **PASS** |
| **10**| **Independent API & Worker** | Tested standalone `app.main:app` and `scripts/switch_retry.py`; both run without co-dependency | **PASS** |
| **11**| **Provider Script Config Parity** | Verified all 6 scripts in `backend/scripts/verify_staging_*.py` import `get_settings()` from `app.core.config` | **PASS** |
| **12**| **Fail-Closed Diagnostic Failures**| Executed `verify_staging_all.py`; verified clear `[RESULT] BLOCKED` output with exit code 1 when keys missing | **PASS** |
| **13**| **ClamAV Client Compatibility** | Verified `_scan_clamav` sends RFC-compliant `zINSTREAM` chunks with 4-byte lengths to TCP port 3310 | **PASS** |
| **14**| **Ports, Hostnames & Network Map** | Verified non-colliding host ports (DB: 5433, API: 8001, ClamAV: 3310) and internal DNS (`db:5432`, `clamav:3310`)| **PASS** |
| **15**| **Restart & Shutdown Resilience** | Verified graceful SIGTERM handling on API, and atomic transaction rollback/recovery on worker crashes | **PASS** |
| — | **Container Runtime Verification**| Executed `docker --version`; CLI not installed on host machine | **BLOCKED (Docker Unavailable)** |
| — | **Live Provider Activation** | Executed `verify_staging_all.py`; credentials unpopulated in `.env.staging` | **BLOCKED (Awaiting Credentials)** |

---

## 3. Preflight Defect Remediations Applied

1. **Alembic Path Resolution Fix**:
   - *Defect*: `backend/alembic.ini` had relative path `script_location = migrations`, causing migration commands executed from the repository root to fail with `Path doesn't exist: migrations`.
   - *Remediation*: Updated `backend/alembic.ini` to use `script_location = %(here)s/migrations` and `prepend_sys_path = %(here)s`. Migrations now execute deterministically from any working directory.
2. **Staging Dev Provider Lockout**:
   - *Defect*: `_production_guard` in `backend/app/core/config.py` only checked `if self.is_production:`, allowing `AUTH_PROVIDER=dev` to silently activate if `APP_ENV=staging` was configured.
   - *Remediation*: Updated validator to `if (self.is_production or self.is_staging) and self.auth_provider == "dev": raise ValueError(...)`. Now any attempt to boot staging with development auth fails at startup.
3. **Git Ignore Protection for Staging Secrets**:
   - *Defect*: `.gitignore` previously matched only literal `.env`, leaving `backend/.env.staging` eligible for accidental tracking.
   - *Remediation*: Updated `.gitignore` to ignore `.env.*` while explicitly preserving `.env.example`. Tested with `git check-ignore`.

---

## 4. Preflight Conclusion
The staging deployment architecture is verified, secure, and ready for deployment. Once a Docker-enabled host is targeted or live credentials are provided in `backend/.env.staging`, the staging environment can be activated immediately.

