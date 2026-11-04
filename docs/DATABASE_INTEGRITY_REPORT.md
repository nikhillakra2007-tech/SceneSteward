# SceneSteward — Database Integrity & Schema Audit Report

**Date**: November 4, 2026  
**Auditor**: Principal PostgreSQL Database Architect & Security Specialist  
**Database**: PostgreSQL 18.6  
**Catalog Current Head**: `e1f2a3b4c5d6` (`migrations/versions/e1f2a3b4c5d6_identity_trust_boundary_and_composite_integrity.py`)  

---

## 1. Migration History & Ledger

The SceneSteward database schema has progressed through 4 linear, idempotent Alembic migrations:

| Revision ID | Description | Key Changes | Applied & Verified |
|:---|:---|:---|:---:|
| `0001_initial` | Initial documentary schema | 16 base tables, initial indexes, enum types | YES |
| `65898c97090c` | Schema adjustments & indexes | Foreign key constraints, unique indexes | YES |
| `c7a1e52b93f0` | Least privilege & RLS | Created `scenesteward_app` role, enabled RLS, 69 policies, immutability triggers | YES |
| `e1f2a3b4c5d6` | Identity trust boundary & composite FKs | Created `private.app_secrets`, HMAC verification functions `app_current_user_id()`, `app_is_system()`, composite FKs `(id, project_id)` | YES |

---

## 2. Table Catalog Breakdown (21 Total Tables)

The database catalog contains exactly 21 tables across schemas `private` and `public`:

### 2.1 Private Schema (1 Table)
- `private.app_secrets`: Stores the HMAC database identity signing secret. Permissions are revoked from all public/application roles; only superuser and `SECURITY DEFINER` routines have access.

### 2.2 Public Non-RLS Tables (2 Tables)
- `public.users`: Global user account repository. Protected by application authentication dependencies and composite join checks.
- `public.alembic_version`: Alembic migration version ledger.

### 2.3 Public Project-Scoped RLS Tables (18 Tables)
All 18 tables have `rowsecurity = true` and `forcerowsecurity = true`:
1. `projects`
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

---

## 3. Catalog Triggers Audit (212 Total Triggers)

A comprehensive inspection of `pg_trigger` shows 212 registered triggers:

### 3.1 Custom Application Business Logic Triggers (4)
1. `trg_audit_events_no_delete` on `audit_events`:
   Raises `CANNOT_DELETE_AUDIT_LOGS` on any `DELETE` operation. Guarantees immutable evidentiary trail for legal compliance.
2. `trg_audit_events_no_update` on `audit_events`:
   Raises `CANNOT_UPDATE_AUDIT_LOGS` on any `UPDATE` operation.
3. `trg_consent_choices_guard` on `consent_choices`:
   Prevents modifying or corrupting active consent choices.
4. `trg_consent_records_guard` on `consent_records`:
   Prevents illegal status reversions or unauthorized state tampering.

### 3.2 Referential Integrity Constraint Triggers (208)
PostgreSQL creates constraint triggers (`RI_ConstraintTrigger_c_*`) for foreign keys. Migration `e1f2a3b4c5d6` reinforced all parent-child relationships with composite foreign keys referencing `(id, project_id)`. This guarantees that a child entity (e.g. `consent_record` or `document`) can never accidentally or maliciously be associated with a different project than its parent `participant` or `project`.

---

## 4. Connection Pool & Transaction Isolation

1. **Transaction Hooks (`before_cursor_execute`)**:
   Every database query executed through SQLAlchemy's async engine sets `LOCAL app.user_id`, `LOCAL app.user_sig`, and timestamp claims inside the active transaction.
2. **Connection Return Hook (`checkin`)**:
   When a connection returns to the connection pool, `DISCARD ALL` and `RESET ALL` are invoked, preventing context leakage between concurrent requests.
3. **Rollback Safety**:
   If a transaction aborts, all `SET LOCAL` variables are immediately discarded by PostgreSQL.

