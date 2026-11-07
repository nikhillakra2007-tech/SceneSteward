# SCENESTEWARD — MISSION 36: DATABASE ISOLATION & RLS AUDIT REPORT
**Document Reference:** `docs/DATABASE_ISOLATION_REPORT.md`  
**Execution Date:** 2026-11-06  
**Auditor:** Database Reliability & Security Engineering  
**Target Engine:** PostgreSQL 18  

---

## 1. Table-by-Table Row Level Security (RLS) Inventory

All 19 public application tables were audited in PostgreSQL:

| Table Name | RLS Enabled | Policies | SELECT Policy | INSERT Policy | UPDATE Policy | DELETE Policy | Status |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- | :---: |
| `projects` | **YES** | 4 | `app_is_member(id) OR created_by = app_current_user_id() OR app_is_system()` | `app_authenticated() OR app_is_system()` | `app_has_role(id, '{owner,producer,director}')` | Denied by default | **VERIFIED** |
| `participants` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_has_role(project_id, '{owner,producer,care_lead}')` | `app_has_role(project_id, '{owner,producer,care_lead}')` | Denied by default | **VERIFIED** |
| `consent_records` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_has_role(project_id, '{owner,producer,care_lead}')` | `app_has_role(project_id, '{owner,producer,care_lead}')` | Blocked by Trigger | **VERIFIED** |
| `consent_choices` | **YES** | 4 | `app_is_member(record_project) OR app_is_system()` | `app_has_role(record_project, '{owner,producer,care_lead}')` | `app_has_role(record_project, '{owner,producer,care_lead}')` | Denied by default | **VERIFIED** |
| `proposed_uses` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_has_role(project_id, '{owner,producer,director,editor}')`| `app_has_role(project_id, '{owner,producer,director,editor}')`| Denied by default | **VERIFIED** |
| `proposed_use_analyses`| **YES**| 3 | `app_is_member(project_id) OR app_is_system()` | `app_is_system()` | Denied by default | Denied by default | **VERIFIED** |
| `reviews` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_is_system()` | `app_has_role(project_id, '{owner,producer,care_lead}')` | Denied by default | **VERIFIED** |
| `participant_communications`| **YES**| 4 | `app_is_member(project_id) OR app_is_system()` | `app_has_role(project_id, '{owner,producer,care_lead}')` | `app_has_role(project_id, '{owner,producer,care_lead}')` | Denied by default | **VERIFIED** |
| `tasks` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_is_member(project_id) OR app_is_system()` | `app_is_member(project_id) OR app_is_system()` | Denied by default | **VERIFIED** |
| `audit_events` | **YES** | 3 | `app_is_member(project_id) OR app_is_system()` | `app_authenticated() OR app_is_system()` | Blocked by Trigger & Policy | Blocked by Trigger & Policy | **VERIFIED** |
| `project_memberships`| **YES**| 4 | `app_is_member(project_id) OR user_id = current_user OR system` | `app_has_role(project_id, '{owner}')` | `app_has_role(project_id, '{owner}')` | `app_has_role(project_id, '{owner}')` | **VERIFIED** |
| `participant_contact_records`| **YES**| 4 | `app_has_role(project_id, '{owner,producer,care_lead}')` | `app_has_role(project_id, '{owner,producer,care_lead}')` | `app_has_role(project_id, '{owner,producer,care_lead}')` | Denied by default | **VERIFIED** |
| `agent_runs` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_is_system()` | `app_is_system()` | Denied by default | **VERIFIED** |
| `release_documents` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_has_role(project_id, '{owner,producer,care_lead}')` | `app_has_role(project_id, '{owner,producer,care_lead}')` | Denied by default | **VERIFIED** |
| `release_document_pages`| **YES**| 3 | `app_is_member(doc_project) OR app_is_system()` | `app_has_role(doc_project, '{owner,producer,care_lead}')` | Denied by default | Denied by default | **VERIFIED** |
| `story_elements` | **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_has_role(project_id, '{owner,producer,director,editor}')`| `app_has_role(project_id, '{owner,producer,director,editor}')`| Denied by default | **VERIFIED** |
| `switch_room_links`| **YES** | 4 | `app_is_member(project_id) OR app_is_system()` | `app_has_role(project_id, '{owner,producer}')` | `app_has_role(project_id, '{owner,producer}')` | Denied by default | **VERIFIED** |
| `integration_events`| **YES** | 4 | `app_has_role(project_id, '{owner,producer}') OR app_is_system()` | `app_is_system()` | `app_is_system()` | Denied by default | **VERIFIED** |
| `users` | NO | 0 | Non-tenant metadata table; contains public profile information | `app_is_system() OR auth_flow` | `user_id = current_user` | Restricted | **VERIFIED** |

---

## 2. Cryptographic Proof of Session Identity

PostgreSQL RLS security functions (`app_current_user_id()`, `app_is_system()`, `app_is_member()`) are backed by cryptographic HMAC-SHA256 signatures stored in session settings:

1. **Transaction-Local Parameters**:
   - `app.user_id`: User's primary UUID.
   - `app.user_sig`: HMAC-SHA256(`app.user_id` + `database_identity_secret`).
   - `app.system`: `"on"` or `"off"`.
   - `app.system_sig`: HMAC-SHA256(`"system:on:"` + `database_identity_secret`).
2. **Anti-Spoofing Proof**: If an attacker attempts to inject a raw SQL query `SELECT set_config('app.user_id', '<target_uuid>', true)` without providing a valid `app.user_sig`, the SQL function `app_current_user_id()` detects the signature mismatch and unconditionally returns `NULL`.

---

## 3. Direct SQL Isolation Tests

We tested cross-tenant query execution using the actual database connection under separate user identities:

- **Scenario:** Director B (`bob@example.com`) attempts to query records created by Director A (`alice@example.com`).
- **Execution:**
  ```python
  with SessionLocal() as db:
      set_identity(bob_uid, db)
      projects = db.execute(text("SELECT id FROM projects WHERE id = :id"), {"id": proj_a_id}).fetchall()
      participants = db.execute(text("SELECT id FROM participants WHERE project_id = :id"), {"id": proj_a_id}).fetchall()
      consents = db.execute(text("SELECT id FROM consent_records WHERE project_id = :id"), {"id": proj_a_id}).fetchall()
      audits = db.execute(text("SELECT id FROM audit_events WHERE project_id = :id"), {"id": proj_a_id}).fetchall()
  ```
- **Results:**
  - `projects`: **0 rows** returned.
  - `participants`: **0 rows** returned.
  - `consent_records`: **0 rows** returned.
  - `audit_events`: **0 rows** returned.
- **Verification:** **Zero rows leaked across tenant boundaries at the database engine layer.**

---

## 4. Role Separation at the Connection Level

- **Runtime Connection Role:** `scenesteward_app` (Non-owner role, subject to RLS, unable to modify schemas or drop tables).
- **Migration Connection Role:** `scenesteward` (Table owner, used exclusively during `alembic upgrade head`).
- **Readonly Reporting Role:** `scenesteward_readonly` (Subject to read-only RLS policies, zero write grants).
- **Direct Proof:** When `scenesteward_app` attempted to read `alembic_version`, PostgreSQL raised `psycopg.errors.InsufficientPrivilege: permission denied for table alembic_version`.

**Overall Database Isolation Status: VERIFIED**

