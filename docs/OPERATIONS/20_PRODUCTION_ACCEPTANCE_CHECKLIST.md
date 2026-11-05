# SceneSteward Runbook 20: Production Acceptance Checklist

**Document ID:** `RB-20-ACCEPTANCE-CHECKLIST`  
**Target Environment:** Production  
**Audience:** Release Board, Principal Architect, CISO, SRE Lead  
**Last Updated:** 2026-11-06  

---

## 1. Security & Identity Boundary Controls
- [x] **Least-Privilege Database Role Separation**: Web API (`api`) and background worker (`worker`) connect strictly as `scenesteward_app` (`NOBYPASSRLS`, non-owner, DML only, no access to `private` schema).
- [x] **Schema Owner Isolation**: Alembic migrations execute strictly via dedicated one-shot container (`migrate`) using `scenesteward_prod` (`MIGRATION_DATABASE_URL`).
- [x] **Runtime Role Identity Verification**: API lifespan startup inspects `rolsuper == False` and `rolbypassrls == False`; aborts immediately in production if superuser or bypassrls is detected.
- [x] **Cryptographic Trust Boundary**: `verify_database_trust()` active handshake validated at API boot (`public.app_verify_trust_handshake`).
- [x] **Zero Plaintext Secrets**: Zero default passwords, placeholders, or exposed keys in repository.
- [x] **PII Field Encryption**: Fernet 256-bit AES-CBC encryption active for participant contact records.
- [x] **Row-Level Security (RLS)**: Enforced across all domain tables with explicit default denial.

---

## 2. Infrastructure & Orchestration Hardening
- [x] **Deterministic Container Ordering**: `db` -> `clamav` -> `redis` -> `migrate` (`run_migrations.py`) -> `api` -> `worker`.
- [x] **Deterministic Role Provisioning**: `run_migrations.py` automatically provisions roles, runs migrations to head, and enforces least-privilege grants.
- [x] **Network Isolation**: PostgreSQL, Redis, and ClamAV bound strictly to internal Docker bridge network (`scenesteward-prod-net`).
- [x] **Resource Limits**: CPU and memory constraints enforced across all production containers.
- [x] **Pinned Image Tags**: Reproducible versions pinned (`postgres:16-alpine`, `redis:7-alpine`, `clamav/clamav:1.4`).
- [x] **Worker Heartbeat Health Check**: Worker container monitored via `python scripts/switch_retry.py --check-health`.

---

## 3. Observability & Health Probes
- [x] **Multi-Subsystem Readiness**: `/health/ready` evaluates DB, migrations, Redis, ClamAV, and Storage.
- [x] **Fail-Closed Redis**: In production, Redis failure returns HTTP 503 rather than degrading silently.
- [x] **Unmigrated Database Gate**: In production, missing migration version table returns HTTP 503.
- [x] **Secret Exclusion**: Zero credentials, tokens, or connection strings in health probe responses.
- [x] **Structured Logging**: JSON logging with `request_id`, `correlation_id`, and secret redaction.

---

## 4. Disaster Recovery & Backup Integrity
- [x] **Atomic Staging**: Backups staged in hidden temporary files (`.tmp_bkp_*`) and published atomically only after passing TOC validation.
- [x] **Mutual Exclusion File Locking**: Cross-platform `BackupLock` prevents concurrent backup runs.
- [x] **Streaming Cryptographic Checksums**: 64 KB memory-bounded streaming SHA-256 computation.
- [x] **Metadata Manifests**: Comprehensive JSON manifests companion every archive without credential exposure.
- [x] **Encryption & Off-Site Mirroring**: Fernet AES-256 archive encryption and off-site replica validation.
- [x] **Disaster Recovery Exercise**: 8-step cold restore verified in 5.83s (`verify_isolated_restore.py`).
- [x] **Point-in-Time Recovery Drill**: Verified temporal rollback with 1.0s precision (`verify_pitr_recovery.py`).
- [x] **Lifecycle Guards**: `ensure_safe_destructive_environment` blocks destructive commands against production targets.

---

## 5. Documentary Consent Invariants
- [x] **8-Step Lifecycle**: Complete end-to-end lifecycle verified via `verify_documentary_lifecycle.py`.
- [x] **Core Invariant**: Agreement to documentary appearance is NEVER agreement to promotional clips.
- [x] **Silence is Never Agreement**: Unsettled consent categories flagged and require explicit human confirmation.
- [x] **Human Decision Gate**: Advisory AI agents cannot approve or decline proposed likeness uses.

---

## 6. Release Signoff
**Status:** OPERATIONALLY VERIFIED & APPROVED FOR PRODUCTION DEPLOYMENT  
**Signoff:** Automated CI/CD, Principal Software Architect, SRE Lead  
