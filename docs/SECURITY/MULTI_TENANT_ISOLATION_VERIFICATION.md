# SceneSteward — Multi-Tenant Isolation Verification

**Status:** Verified & Adversarially Tested  
**Date:** 2026-11-06  
**Auditors:** PostgreSQL Database Architect, Application Security Lead  
**Scope:** PostgreSQL Row Level Security (RLS), Composite Keys, HMAC-Signed Identity Handshake  

---

## 1. Architectural Tenant Isolation Model

SceneSteward implements an isolated multi-tenant data architecture where each production documentary project is an isolated tenant domain.

Isolation is enforced at two independent layers:
1. **Application-Layer Authorization:** FastAPI dependencies verify project membership (`get_membership()`) on all entity routes.
2. **Database-Layer Row Level Security (RLS):** PostgreSQL enforces row-level policies directly inside the database query execution planner. Even if application-layer checks were bypassed or raw SQL was injected, the database engine filters out rows belonging to other projects.

```
       +-------------------------------------------------------+
       |           Incoming Request (Bearer / Token)           |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |   Layer 1: FastAPI Dependency (RBAC & Membership)     |
       |     * Verifies user membership in project             |
       |     * Rejects foreign tenant IDs with HTTP 404/403    |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |   HMAC-SHA256 Handshake (app.core.database)           |
       |     * Computes identity signature with secret         |
       |     * Injects app.user_id + app.user_sig into session |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |   Layer 2: PostgreSQL Engine (Row Level Security)     |
       |     * Validates HMAC signature via app_verify_user()  |
       |     * Evaluates project_id IN (user's memberships)    |
       |     * Completely isolates row visibility              |
       +-------------------------------------------------------+
```

---

## 2. PostgreSQL RLS Policies & Trust Boundary

### 2.1 The Cryptographic Signature Handshake
PostgreSQL session settings (`set_config('app.user_id', ...)`) can technically be written by any active connection unless protected. To prevent SQL injection from spoofing arbitrary user IDs, SceneSteward uses an HMAC-SHA256 signature verification function defined in migration `20261105_02_database_identity_secret`:

```sql
CREATE OR REPLACE FUNCTION app_verify_identity(p_user_id text, p_sig text)
RETURNS boolean AS $$
DECLARE
    v_secret text;
    v_expected text;
BEGIN
    SELECT secret_val INTO v_secret FROM private.app_secrets WHERE key_name = 'identity_secret';
    IF v_secret IS NULL OR p_sig IS NULL OR p_user_id IS NULL THEN
        RETURN false;
    END IF;
    v_expected := encode(hmac(p_user_id, v_secret, 'sha256'), 'hex');
    RETURN (v_expected = p_sig);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 2.2 System Context Bypass Protection
System operations (such as outbox workers or background tasks) operate within `system_context(db)`:
- Sets `app.system = 'on'`.
- Injects `app.system_sig = HMAC("system", identity_secret)`.
- If an attacker injects `app.system = 'on'` without a matching HMAC signature, `app_verify_system()` returns `false`, causing all queries to return zero rows.

---

## 3. Adversarial Multi-Tenant Test Results

The test suite in `backend/tests/security/test_trust_boundary.py` and `backend/tests/security/test_production_hardening.py` executes adversarial attacks against the database:

1. **User Spoofing via Raw SQL:**
   - Attacker executes `SET app.user_id = '<victim_uuid>'` without `app.user_sig`.
   - Result: 0 rows returned. Attack prevented.
2. **System Context Spoofing:**
   - Attacker executes `SET app.system = 'on'` without valid `app.system_sig`.
   - Result: 0 rows returned. Attack prevented.
3. **Cross-Project Referential Injection:**
   - Attacker attempts to insert a `consent_record` referencing `project_id_A` and `participant_id_B` (who belongs to `project_id_B`).
   - Result: Database rejects the insert due to composite foreign key constraint `fk_consent_records_participant_project`.
4. **Secret Table Access:**
   - Attacker running under the runtime role `scenesteward_app` attempts `SELECT * FROM private.app_secrets`.
   - Result: PostgreSQL rejects with `ERROR: permission denied for schema private`.
5. **Cross-Tenant Clarification Task Creation:**
   - Staff user belonging to Tenant B attempts to create clarification task on Tenant A's participant.
   - Result: HTTP 404 returned; no task created; no cross-tenant leakage.

---

## 4. Verdict

Multi-tenant isolation in SceneSteward has been thoroughly validated. The combination of application-level membership checks and database-level RLS policies provides robust defense in depth.

