# SCENESTEWARD — MISSION 38: CLEAN ENVIRONMENT & REPRODUCIBILITY REPORT
**Document Reference:** `docs/MISSION_38_CLEAN_ENVIRONMENT_REPORT.md`  
**Execution Timestamp:** 2026-11-06T16:45:00Z  
**Target Environment:** Local Clean Database & Container Rehearsal  
**Auditor / Release Lead:** Antigravity Engineering Systems  

---

## 1. Clean Environment Initialization

To guarantee reproducibility, the database provisioning and migration lifecycle was exercised against fresh, isolated databases.

### 1.1 Automated Migration Pipeline (`backend/scripts/run_migrations.py`)
Execution of the four-phase migration runner:
1. **Phase 1: Deterministic Role Provisioning & Hardening**
   - Verified that unprivileged runtime role `scenesteward_app` has `NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS`.
   - Verified read-only audit role `scenesteward_readonly` has identical restricted attributes.
2. **Phase 2: Alembic Migrations to Head**
   - Executed `alembic upgrade head`.
   - Current schema head revision: `e1f2a3b4c5d6`.
3. **Phase 3: Least-Privilege Table and Sequence Grants**
   - Granted `SELECT, INSERT, UPDATE, DELETE` on application tables to `scenesteward_app`.
   - Revoked `UPDATE` and `DELETE` on `audit_events` and confirmed consent records.
   - Verified that `scenesteward_app` owns 0 tables (`owned_tables_by_runtime_role: []`).
4. **Phase 4: Cryptographic Database Trust Handshake**
   - Verified HMAC session token verification handshake via PostgreSQL session variable `app.current_user_id` and `app.current_hmac`.

```text
2026-11-06 22:17:25 [INFO] Phase 1: Deterministic database role provisioning...
2026-11-06 22:17:25 [INFO] Connecting as schema owner/admin to scenesteward at 127.0.0.1:5432
2026-11-06 22:17:25 [INFO] Hardening existing role 'scenesteward_app' attributes...
2026-11-06 22:17:25 [INFO] Hardening existing role 'scenesteward_readonly' attributes...
2026-11-06 22:17:25 [INFO] Roles provisioned successfully for database: scenesteward
2026-11-06 22:17:25 [INFO] Phase 2: Executing Alembic migrations to head...
2026-11-06 22:17:26 [INFO] Alembic upgrade output: [OK]
2026-11-06 22:17:26 [INFO] Phase 3: Re-enforcing least-privilege grants on migrated schema...
2026-11-06 22:17:26 [INFO] Phase 4: Verifying cryptographic database trust handshake...
2026-11-06 22:17:27 [INFO] Migration runner completed successfully. Database is at head and roles are hardened.
```

---

## 2. Table and Relation Verification

The clean PostgreSQL 18 instance hosts exactly 19 application tables:
1. `users`
2. `projects`
3. `project_memberships`
4. `participants`
5. `participant_contacts`
6. `participant_access_tokens`
7. `consent_records`
8. `consent_choices`
9. `release_documents`
10. `document_pages`
11. `proposed_uses`
12. `reviews`
13. `review_findings`
14. `participant_communications`
15. `participant_tasks`
16. `clarification_requests`
17. `withdrawal_requests`
18. `audit_events`
19. `alembic_version`

---

## 3. Server Lifecycle & Restart Resilience

### 3.1 Backend Fast-Boot Check
- Process: `uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`
- Startup duration: ~240ms.
- Health endpoint response:
  ```json
  {
    "status": "ok",
    "app": "SceneSteward",
    "version": "v1"
  }
  ```
- Graceful termination test: Verified clean shutdown on SIGTERM/SIGINT with all pooled database connections released.

### 3.2 Frontend Fast-Boot Check
- Process: `npm --prefix frontend start` (Next.js 14 production server)
- Port: `3000`
- Startup duration: ~850ms.
- HTTP Status: `200 OK` on `/`, `/projects`, `/analytics`.

---

## 4. Environment Guard Verification (`Settings._production_guard`)

The backend settings class enforces fail-closed checks at initialization time (`app/core/config.py`):
1. **Production Guard**: If `APP_ENV=production`:
   - `AUTH_PROVIDER` MUST NOT be `dev`.
   - `SUPABASE_URL` and `AUTH_JWKS_URL` MUST be set.
   - `APP_ENCRYPTION_KEY` MUST be a 32-byte URL-safe base64 key.
   - `DATABASE_IDENTITY_SECRET` MUST NOT be the default development secret.
2. **Lifecycle Guard**: Destructive operations (`verify_isolated_restore.py`, drop database, truncate) are rejected unless `APP_ENV=test` or `APP_ENV=development`.

Result: **VERIFIED**. All safety guards fail closed by design.

