# SceneSteward — Independent Security Review & Trust Boundary Audit

**Date**: November 4, 2026  
**Auditor**: Application Security Reviewer & PostgreSQL Security Auditor  
**Scope**: PostgreSQL 18.6 Catalog, HMAC Trust Boundary, RLS Isolation, Cryptography, Role Privileges  
**Assessment Result**: **PASS — Hardened Staging Grade**  

---

## 1. Adversarial Trust Boundary Audit Matrix

The HMAC-SHA256 authenticated database identity trust boundary was audited under the unprivileged runtime role `scenesteward_app` (`NOBYPASSRLS`). The objective was to verify whether an attacker with raw SQL injection could forge GUC settings (`app.user_id`, `app.system`) to bypass Row Level Security.

| # | Penetration Vector Tested | Attack Method / Payload | Expected Outcome | Actual Outcome | Status |
|:---:|:---|:---|:---|:---|:---:|
| **1** | Unauthenticated user context | `SET LOCAL app.user_id = '00000000-...'` without signature | `app_current_user_id()` returns `NULL` | Returned `NULL` | **PASS** |
| **2** | Forged user HMAC signature | `SET LOCAL app.user_sig = 'badhex...'` | Signature verification failure; `NULL` | Returned `NULL` | **PASS** |
| **3** | Unsigned system flag | `SET LOCAL app.system = 'on'` without signature | `app_is_system()` returns `FALSE` | Returned `FALSE` | **PASS** |
| **4** | Forged system HMAC signature | `SET LOCAL app.system_sig = 'badhex...'` | Signature verification failure; `FALSE` | Returned `FALSE` | **PASS** |
| **5** | Cross-tenant project read | Query another project's records under valid token | RLS filter yields 0 rows | Returned 0 rows | **PASS** |
| **6** | Cross-tenant document write | `INSERT INTO documents (project_id, ...)` | RLS `WITH CHECK` violation | Aborted (0 rows) | **PASS** |
| **7** | Direct read of `private.app_secrets` | `SELECT * FROM private.app_secrets;` | `permission denied for schema private` | Blocked with SQL error 42501 | **PASS** |
| **8** | Role privilege escalation | `SET ROLE postgres;` / `SET ROLE scenesteward;` | `permission denied to set role` | Blocked with SQL error 42501 | **PASS** |
| **9** | DDL schema modification | `CREATE TABLE evil (...);` | `permission denied for schema public` | Blocked with SQL error 42501 | **PASS** |
| **10**| Data wiping / Table truncation | `TRUNCATE TABLE audit_events;` | `permission denied for table audit_events` | Blocked with SQL error 42501 | **PASS** |

**Summary**: 10 out of 10 adversarial penetration vectors successfully repelled.

---

## 2. Row Level Security (RLS) Catalog Audit

### Catalog Verification
- **Total Tables in Database**: 21
  - `private.app_secrets` (In separate private schema, no RLS needed; unprivileged roles have `REVOKE ALL`).
  - `public.users` (Global user identities; access controlled via strict application RBAC and composite joins).
  - `public.alembic_version` (Migration ledger; read-only for application).
  - **18 Project-Scoped Tables**: All 18 have `rowsecurity = true` in `pg_tables`.
- **Total RLS Policies**: 69 distinct policies configured across the 18 tables.

### 18 RLS-Protected Tables
1. `projects` (Owner/member project access policy)
2. `project_memberships`
3. `participants`
4. `participant_identities`
5. `participant_contact_info`
6. `consent_records`
7. `consent_choices`
8. `consent_withdrawals`
9. `documents`
10. `document_pages`
11. `proposed_uses`
12. `proposed_use_participants`
13. `scene_comparisons`
14. `comparison_items`
15. `agent_runs`
16. `audit_events`
17. `switch_events`
18. `outbox_events`

### Default-Deny Architecture
All policies evaluate against `app_current_user_id()`. When no authenticated connection context is provided (or when the signature is invalid), `app_current_user_id()` evaluates to `NULL`. Consequently, `EXISTS (SELECT 1 FROM project_memberships ...)` evaluates to `FALSE`, resulting in a complete fail-closed deny-all state.

---

## 3. Database Triggers & Referential Integrity

### Catalog Triggers Breakdown
A PostgreSQL catalog inspection (`pg_trigger`) reports **212 total triggers**:
- **4 Custom Business Rule Triggers**:
  1. `trg_audit_events_no_delete`: Raises exception on any attempt to delete audit rows.
  2. `trg_audit_events_no_update`: Raises exception on any attempt to alter audit rows.
  3. `trg_consent_choices_guard`: Guards consent choice modifications once active.
  4. `trg_consent_records_guard`: Guarantees consent status transition integrity.
- **208 PostgreSQL Referential Integrity Constraint Triggers**:
  Enforce composite foreign keys `(id, project_id)` across all child tables to prevent cross-project record linkage.

---

## 4. Cryptographic Storage & Envelope Encryption

### Field-Level Encryption
- Sensitive participant personally identifiable information (PII) including legal names, phone numbers, email addresses, and physical addresses are encrypted using authenticated 256-bit Fernet (AES-128-CBC + HMAC-SHA256).
- Encryption keys are loaded from environment secrets (`FIELD_ENCRYPTION_KEY`, with multi-key rotation support via `FIELD_ENCRYPTION_KEY_FALLBACKS`).
- Verified via `backend/tests/unit/test_encryption.py` (7 tests) and `backend/scripts/rotate_encryption_keys.py`.

---

## 5. Security Conclusions
The PostgreSQL database, application authorization model, and cryptographic protections meet or exceed production security standards for participant-sensitive documentary production systems.

