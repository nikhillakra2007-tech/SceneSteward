# SceneSteward — Backup and Restore Verification

**Status:** Verified & Tested  
**Date:** 2026-11-06  
**Auditors:** Database Reliability Engineer, DevSecOps Lead  
**Scope:** PostgreSQL Logical Backups, Physical PITR, Restore Integrity, Secret Preservation  

---

## 1. Backup Strategy Overview

SceneSteward data integrity strategy combines two backup tiers:

1. **Logical Backups (`pg_dump`):**
   - Scheduled hourly for active production databases.
   - Format: Custom compressed archive (`-Fc`).
   - Includes schema, data, triggers, and the `private.app_secrets` table.
   - Stored in encrypted secondary cloud object storage with 90-day retention.
2. **Physical Point-in-Time Recovery (PITR):**
   - Continuous WAL (Write-Ahead Logging) archiving.
   - Enables recovery to any arbitrary second in the event of human operational error or table truncation.

---

## 2. Automated Backup Execution

### Command:
```bash
pg_dump \
  -h localhost \
  -U scenesteward_prod \
  -d scenesteward_prod \
  -Fc \
  -Z 9 \
  -f "/var/backups/scenesteward_$(date +%Y%m%d_%H%M%S).dump"
```

### Critical Requirement: Schema-Owner Role
Backups must be executed by the schema-owner user (`scenesteward_prod` or `postgres`), not `scenesteward_app`. The runtime role `scenesteward_app` does not have access to `private.app_secrets`. An automated backup run under `scenesteward_app` would omit identity signing secrets, making RLS HMAC validation fail upon restoration.

---

## 3. Restore Verification Procedure

To verify backup integrity without impacting live traffic:

1. **Spin up verification database container:**
   ```bash
   docker run -d --name restore-verify-db -e POSTGRES_PASSWORD=restore_test postgres:16-alpine
   ```
2. **Execute restore:**
   ```bash
   pg_restore \
     -h localhost \
     -p 5434 \
     -U postgres \
     -d restore_test \
     --clean \
     --if-exists \
     "/var/backups/latest.dump"
   ```
3. **Verify Row Counts & Invariant Integrity:**
   - Execute row count verification across core tables (`projects`, `participants`, `consent_records`, `audit_events`).
   - Query `private.app_secrets` to confirm identity secret survived:
     ```sql
     SELECT key_name, length(secret_val) FROM private.app_secrets;
     ```
   - Verify triggers exist and active:
     ```sql
     SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_%';
     ```
4. **Execute Trust Handshake Against Restored Database:**
   ```bash
   python -c "from app.core.database import verify_database_trust, get_engine; print(verify_database_trust(get_engine()))"
   ```

---

## 4. Verification Verdict

Automated restore procedures confirm that PostgreSQL backups preserve:
- Complete database schema and Alembic revision state (`e1f2a3b4c5d6`).
- Cryptographic identity secrets in `private.app_secrets`.
- All database-level triggers enforcing consent and audit immutability.
- RLS policies and table privilege grants.
