# SceneSteward — Architecture and Deployment Deep Inspection Report

**Document ID:** `DOC-OPS-00-INSPECTION`  
**Date:** 2026-11-05  
**Baseline Git Commit:** `b9227bec007ba11ce20bee22d8a68e257818e782`  
**Target Branch:** `deployment/production-readiness`  
**Status:** COMPLETE & VERIFIED  

---

## Executive Summary

Before implementing production deployment hardening, release automation, and operational runbooks, an exhaustive architectural and deployment inspection of the SceneSteward codebase was executed.

This report establishes the baseline architecture, service orchestration topology, database initialization workflows, configuration matrices, security trust boundaries, health check implementations, operational risks, and the concrete implementation plan for achieving full production maturity.

---

## 1. Current Architecture

SceneSteward is built on a resilient, modular, defense-in-depth architecture designed for documentary consent management.

```
+-----------------------------------------------------------------------------------+
|                                  CLIENT LAYER                                     |
|  - Next.js 14 App Router (React 18, TypeScript, Tailwind CSS, Lucide Icons)      |
|  - Public/Participant Portal (Identity Verification, Consent Review, Signatures) |
|  - Production Crew Admin Dashboard (Ledgers, Invariant Gates, Scene Audit)        |
+-----------------------------------------------------------------------------------+
                                         | HTTPS / WSS
                                         v
+-----------------------------------------------------------------------------------+
|                                  INGRESS LAYER                                    |
|  - Reverse Proxy (TLS Termination, Rate Limiting, Proxy Protocol Header Injection)|
+-----------------------------------------------------------------------------------+
                                         | HTTP / Host Port 8000
                                         v
+-----------------------------------------------------------------------------------+
|                             BACKEND API LAYER (FastAPI)                           |
|  - Lifespan Bootstrapper: Logging -> Env Validation -> Database Trust Handshake   |
|  - Security Middleware: Security Headers, Request Tracing, Distributed Rate Limit |
|  - Application Routers (/api/v1/projects, /participants, /agreements, /scenes...) |
|  - Health & Probes: /health, /health/live, /health/ready                          |
+-----------------------------------------------------------------------------------+
         |                    |                   |                   |
         v                    v                   v                   v
+-----------------+  +-----------------+  +---------------+  +---------------------+
| POSTGRESQL 16   |  | REDIS 7 (CACHE) |  | CLAMAV DAEMON |  | EXTERNAL SERVICES   |
| - Non-owner RLS |  | - Rate limiting |  | - Antivirus   |  | - Supabase Auth/S3  |
| - HMAC Trust Sig|  | - Append-only   |  | - Port 3310   |  | - Anthropic Claude  |
| - 3 DB Roles    |  | - Password auth |  | - TCP socket  |  | - Switch Core API   |
+-----------------+  +-----------------+  +---------------+  +---------------------+
         ^
         | Transactional Outbox (switch_outbox table)
+-----------------------------------------------------------------------------------+
|                        TRANSACTIONAL OUTBOX WORKER                                |
|  - scripts/switch_retry.py (--loop daemon mode)                                   |
|  - At-least-once guaranteed delivery, exponential backoff, dead-letter tracking   |
+-----------------------------------------------------------------------------------+
```

### Core Architecture Components:
1. **API Web Server**: FastAPI Python 3.12 running under Uvicorn with `--proxy-headers` and multiple workers.
2. **Database Engine**: PostgreSQL 16+ utilizing Row Level Security (RLS) on all multi-tenant tables.
3. **Cryptographic Identity Trust Boundary**: Transactions set `app.user_id` alongside `app.user_sig` (HMAC-SHA256 signature). PostgreSQL validates signatures against `private.app_secrets`.
4. **Three Tiered Database Roles**:
   - `scenesteward`: Database owner, runs Alembic schema migrations, owns DDL.
   - `scenesteward_app`: Unprivileged runtime role, `NOBYPASSRLS`, DML only, denied access to `private.app_secrets`.
   - `scenesteward_readonly`: Read-only analytical role, `NOBYPASSRLS`.
5. **PII Field Encryption**: AES-256-CBC (Fernet) field-level encryption for sensitive participant contact information with versioned key ring rotation support.
6. **Transactional Outbox Worker**: Python background worker polling `switch_outbox` to synchronize consent state with external production ecosystems (Switch Core).
7. **Distributed Rate Limiting**: Redis-backed token bucket algorithm with graceful fail-safe behavior.
8. **Malware Defense**: ClamAV daemon (`clamd`) TCP socket integration with fail-closed configuration option.
9. **AI Document Intelligence**: Anthropic Claude API (`claude-sonnet-4-5`) with structured JSON schema outputs and offline deterministic fallback.

---

## 2. Service Dependency Map

| Service Name | Internal Container Name | Depends On | Dependency Condition | Role in System |
| :--- | :--- | :--- | :--- | :--- |
| `db` | `scenesteward-prod-db` | None (Root) | Starts first | Primary relational datastore, RLS enforcement |
| `redis` | `scenesteward-prod-redis` | None (Root) | Starts first | Distributed rate-limiting and session counters |
| `clamav` | `scenesteward-prod-clamav` | None (Root) | Starts first | Antivirus scanning daemon |
| `migrate` | `scenesteward-prod-migrate` | `db` | `service_healthy` | Executes Alembic schema migrations to `head` |
| `api` | `scenesteward-prod-api` | `db`<br>`redis`<br>`clamav`<br>`migrate` | `service_healthy`<br>`service_healthy`<br>`service_healthy`<br>`service_completed_successfully` | Core web application API handling HTTP traffic |
| `worker` | `scenesteward-prod-worker` | `db`<br>`api` | `service_healthy`<br>`service_healthy` | Transactional outbox asynchronous event processor |

---

## 3. Deployment Topology

### Environments:
1. **Local Development (`APP_ENV=development`)**:
   - Single-host Docker stack (`docker-compose.yml`) or bare-metal virtualenv + PostgreSQL.
   - Dev authentication provider (`AUTH_PROVIDER=dev`), offline AI (`AI_PROVIDER=offline`), local storage (`STORAGE_PROVIDER=local`).
2. **Staging Environment (`APP_ENV=staging`)**:
   - Docker Compose staging stack (`docker-compose.staging.yml`) on an isolated bridge network `scenesteward-staging-net`.
   - Explicit secrets from `backend/.env.staging`.
   - Real Supabase Auth, real ClamAV daemon, live or mock external integrations.
3. **Production Environment (`APP_ENV=production`)**:
   - Hardened multi-container production stack (`docker-compose.prod.yml`).
   - Strict network boundary: only port 8000 exposed to reverse proxy; `db`, `redis`, `clamav` strictly internal.
   - Resource limits (CPU and Memory quotas) applied to all services.
   - Healthcheck retry intervals tuned for production stability.

---

## 4. Startup Sequence

```
[Phase 1: Datastores & Daemons Boot]
       |
       +---> db (PostgreSQL) boots -> runs healthcheck (pg_isready)
       |
       +---> redis (Redis 7) boots with --requirepass -> runs healthcheck (redis-cli ping)
       |
       +---> clamav (ClamAV daemon) boots -> downloads/loads CVD definitions -> binds port 3310
       |
[Phase 2: Database Schema & Migration Execution]
       |
       +---> migrate container boots when db is healthy
       |       - Connects as schema owner (MIGRATION_DATABASE_URL)
       |       - Runs `alembic -c alembic.ini upgrade head`
       |       - Verifies cryptographic HMAC secret in private.app_secrets
       |       - Exits with status code 0
       |
[Phase 3: Core API Boot & Lifespan Verification]
       |
       +---> api container boots when db, redis, clamav are healthy & migrate completed
       |       - Loads environment configuration via Pydantic BaseSettings
       |       - Validates no default passwords or dev auth in staging/production
       |       - Executes verify_database_trust() active cryptographic handshake
       |       - Binds Uvicorn to 0.0.0.0:8000
       |       - Passes /health/ready probe
       |
[Phase 4: Asynchronous Processing Boot]
       |
       +---> worker container boots when db and api are healthy
               - Connects to PostgreSQL under scenesteward_app
               - Begins polling switch_outbox in continuous loop
```

---

## 5. Database Initialization Sequence

When initializing a new environment from scratch:

1. **PostgreSQL Database Cluster Creation**:
   - Cluster created with UTF-8 encoding.
   - Superuser/owner role creates target database (`scenesteward_prod` or `scenesteward_staging`).
2. **Role Creation (`backend/scripts/db_roles.sql`)**:
   - Creates `scenesteward_app` with `LOGIN`, `PASSWORD`, `NOBYPASSRLS`, `NOINHERIT`.
   - Creates `scenesteward_readonly` with `LOGIN`, `PASSWORD`, `NOBYPASSRLS`, `NOINHERIT`.
3. **Schema Migration Execution (Alembic)**:
   - Migration `20241001_0001` initializes core relational tables: `projects`, `participants`, `agreements`, `scenes`, `events`, `reviews`.
   - Migration `c7a1e52b93f0` enables Row Level Security (RLS) on all public tables.
   - Migration `20261105_0007` creates `private.app_secrets`, cryptographic trust functions `app_verify_trust_handshake`, `app_current_user_id`, `app_is_system`, and injects initial trust secret.
4. **Permission Grants**:
   - Grants `USAGE` on schema `public` to `scenesteward_app` and `scenesteward_readonly`.
   - Grants `SELECT, INSERT, UPDATE, DELETE` on all tables in schema `public` to `scenesteward_app`.
   - Grants `USAGE, SELECT` on all sequences to `scenesteward_app`.
   - Grants `SELECT` only to `scenesteward_readonly`.
   - Explicitly ensures zero permissions granted to `private` schema.

---

## 6. External Integration Map

| Integration | Provider | Authentication | Protocol | Failure Mode Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Authentication** | Supabase Auth | RS256/ES256 JWKS via HTTPS | REST / JWKS | Fail closed (HTTP 401 Unauthorized) |
| **Storage** | Supabase Storage / S3 | HMAC Signature / Bearer Token | HTTPS S3 API | Fail closed (HTTP 500 / retryable upload error) |
| **Antivirus** | ClamAV Daemon | Network Socket (Port 3310) | ClamAV Protocol | Fail closed (`ANTIVIRUS_FAIL_CLOSED=true` in prod) |
| **AI Intelligence** | Anthropic API | API Key (`x-api-key`) | HTTPS REST | Fallback to deterministic rule engine or fail gracefully |
| **Collaboration** | Switch Core API | Bearer Token + Webhook HMAC | HTTPS REST | Retry via transactional outbox worker with exponential backoff |
| **Rate Limiter** | Redis 7 | Auth Password (`requirepass`) | Redis TCP | Fail open for user traffic if Redis down, log critical alert |

---

## 7. Persistent Data Inventory

| Volume Name | Container Path | Data Type | Criticality | Backup Strategy | RPO / RTO Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scenesteward-prod-pgdata` | `/var/lib/postgresql/data` | Relational tables, consent ledgers, audit trails, trust secrets | **Critical** | Hourly pg_dump, WAL archiving | RPO < 15 min<br>RTO < 30 min |
| `scenesteward-prod-storage` | `/srv/scenesteward/backend/var/storage` | PDF agreements, identity documents, scan attachments | **High** | Daily incremental snapshot | RPO < 1 hour<br>RTO < 2 hours |
| `scenesteward-prod-clamav` | `/var/lib/clamav` | Antivirus definition databases (`daily.cvd`, etc.) | **Low** | Ephemeral, redownloadable via freshclam | N/A |
| `scenesteward-prod-redis` | `/data` | Rate limiting sliding window counters, session caches | **Low** | Append-only file (AOF), rebuildable | N/A |

---

## 8. Configuration Inventory

### Environment Variables & Validation Rules:

| Variable | Staging | Production | Description / Validation Rule |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `staging` | `production` | Enforces production guards (no dev auth, no default secrets) |
| `DATABASE_URL` | Required | Required | Connection string for `scenesteward_app` (NOBYPASSRLS) |
| `MIGRATION_DATABASE_URL` | Required | Required | Connection string for schema owner (`scenesteward`) |
| `DATABASE_IDENTITY_SECRET` | Required | Required | Minimum 32 characters, high entropy, zero placeholder strings |
| `AUTH_PROVIDER` | `supabase` | `supabase` | Must NOT be `dev` in staging/production |
| `SUPABASE_URL` | Required | Required | Supabase project URL |
| `SUPABASE_ANON_KEY` | Required | Required | Supabase client anon public key |
| `APP_ENCRYPTION_KEY` | Required | Required | 256-bit AES Fernet base64 key; verified at boot |
| `APP_ENCRYPTION_CURRENT_KID`| Required | Required | Key ID for primary encryption key |
| `APP_ENCRYPTION_KEYS` | Required | Required | JSON dictionary of valid key ring identifiers |
| `ANTIVIRUS_PROVIDER` | `clamav` | `clamav` | Antivirus engine (`clamav` required in live environments) |
| `CLAMAV_HOST` | `clamav` | `clamav` | ClamAV service hostname in Docker network |
| `ANTIVIRUS_FAIL_CLOSED` | `true` | `true` | Must be `true` in production; prevents unscanned uploads |
| `REDIS_URL` | Optional | Required | Redis connection string with authenticated password |
| `REDIS_PASSWORD` | Optional | Required | High-entropy password for Redis instance |
| `FRONTEND_ORIGIN` | Required | Required | Allowed CORS origin URL |

---

## 9. Health & Readiness Checks

### Current Implementation Status:
- `/health` & `/health/live`: Basic liveness probe returning `{"status": "ok", "app": "SceneSteward"}`.
- `/health/ready`: Currently checks only database connectivity (`SELECT 1`). Returns HTTP 200 even if degraded.
- ClamAV container healthcheck: Uses `clamdscan /etc/passwd || exit 0`, which masks actual daemon failures.
- Redis container healthcheck in prod: Uses `redis-cli ping` without authentication, which fails when `--requirepass` is set.

### Target Readiness Contract:
- `/health/ready` must evaluate:
  1. PostgreSQL database connectivity.
  2. Database migration status (schema verification).
  3. Redis connectivity and latency (if configured).
  4. ClamAV daemon connectivity (if configured).
  5. Local/Cloud storage accessibility.
- Status code: **HTTP 200 OK** when all critical services pass; **HTTP 503 Service Unavailable** when critical dependencies fail.
- Secret Sanitization: Health response must never expose connection strings, passwords, or internal file paths.

---

## 10. Deployment Risks Discovered

1. **Staging Insecure Default Fallbacks**:
   - `docker-compose.staging.yml` contained fallbacks (`staging_db_secure_pass_2026`, `scenesteward_staging_identity_trust_secret_2026`). If `.env.staging` was omitted, the stack booted with insecure known secrets, which were also blocked by `config.py` validators, causing startup aborts.
2. **Production Redis Command Password Fallback**:
   - `docker-compose.prod.yml` used `--requirepass "${REDIS_PASSWORD:-}"`. If unset, Redis allowed unauthenticated commands. Furthermore, `redis-cli ping` failed when a password was provided.
3. **ClamAV Healthcheck Masking**:
   - Both staging and production ClamAV containers used `|| exit 0` in their healthcheck, causing Docker to mark ClamAV as "healthy" even if `clamd` failed to start or crashed.
4. **PostgreSQL Mount Path Inconsistency**:
   - `docker-compose.staging.yml` mounted `/var/lib/postgresql`, whereas `docker-compose.prod.yml` mounted `/var/lib/postgresql/data`. Alpine Postgres uses `/var/lib/postgresql/data` by default as `PGDATA`.
5. **Container Image Reproducibility**:
   - `clamav/clamav:latest` was unpinned, risking unpredictable image updates in production.
6. **Readiness Probe HTTP Status Code**:
   - `/health/ready` returned HTTP 200 even when `check_database()` reported `unavailable`.

---

## 11. Missing Functionality to Address

1. **Comprehensive `/health/ready` Subsystem Probes**:
   - Integrate multi-service readiness checks (DB, Redis, ClamAV, Storage) with HTTP 503 error handling.
2. **Active ClamAV Daemon Healthcheck**:
   - Real TCP socket probe to verify `clamd` is actively accepting scan requests.
3. **Production Redis Auth Probe**:
   - Healthcheck command with proper password argument: `redis-cli -a "$${REDIS_PASSWORD}" ping`.
4. **Production Configuration Template**:
   - Creation of `backend/.env.production.example` documenting all production secrets and configurations.
5. **Operational Runbooks**:
   - Complete documentation of 20 mission-critical runbooks in `docs/OPERATIONS/`.

---

## 12. Recommended Implementation Plan

1. **Phase 1: Configuration & Container Hardening**:
   - Remove fallback defaults from `docker-compose.staging.yml` and `docker-compose.prod.yml`.
   - Standardize Postgres volume mounts to `/var/lib/postgresql/data`.
   - Pin container image versions (`clamav/clamav:1.4`, `postgres:16-alpine`, `redis:7-alpine`).
   - Create `backend/.env.production.example`.
2. **Phase 2: Startup & Service Orchestration**:
   - Verify deterministic startup ordering (`db` -> `migrate` -> `api` -> `worker`).
   - Ensure migration container must complete successfully before API starts.
3. **Phase 3: Health, Readiness & Observability**:
   - Implement comprehensive `/health/ready` endpoint in `backend/app/api/health.py`.
   - Fix container health checks for ClamAV and Redis.
4. **Phase 4: Documentary Lifecycle & Invariant Verification**:
   - Execute and verify the complete 8-step documentary lifecycle workflow.
5. **Phase 5: External Integration Failure-Mode Testing**:
   - Verify resilient failure modes for Supabase, ClamAV, Redis, and Switch.
6. **Phase 6: Backup, Restore & Disaster Recovery**:
   - Author and verify automated backup and isolated restore verification tooling.
7. **Phase 7: CI/CD & Release Automation**:
   - Verify GitHub Actions workflow and Docker build pipelines.
8. **Phase 8: Concurrency & Performance Testing**:
   - Verify database pooling and rate limiting under concurrent load.
9. **Phase 9: Operational Runbooks Delivery**:
   - Author all 20 runbooks under `docs/OPERATIONS/`.
10. **Phase 10: Final Verification & PR Delivery**:
    - Run full test suite, lint check, frontend build, push branch, open PR, and verify green CI.

---
*Inspection completed and approved for Phase 1 execution.*
