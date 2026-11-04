# SceneSteward — Database Security & Row Level Security (RLS) Architecture

## 1. Threat Model & Database Access Paths

SceneSteward persistence adheres strictly to **defense in depth** and **least privilege**.
Persisted state in PostgreSQL is the authoritative source of truth.

| Access Path | Database Role | Permissions | Allowed Tables | Allowed Ops | Tenant Scope | Bypasses RLS? | Sensitive Participant Data |
|---|---|---|---|---|---|---|---|
| Authenticated API Requests | `scenesteward_app` | DML only | All public tables | SELECT, INSERT, UPDATE, DELETE (subject to RLS) | Bound to `app.user_id` active memberships | **NO** | Restricted to `project_owner`, `producer`, `participant_care_lead`, or participant self |
| Read-only Reporting | `scenesteward_readonly` | SELECT only | All public tables | SELECT only | Bound to `app.user_id` active memberships | **NO** | Restricted by RLS policies |
| Background Sweeper / Listener | `scenesteward_app` (with `app.system='on'`) | DML only | `tasks`, `integration_events`, `switch_room_links` | SELECT, INSERT, UPDATE | System worker scope | **NO** (allowed via `app_is_system()`) | No raw contact data accessed |
| Agent Execution | `scenesteward_app` (with `app.system='on'`) | DML only | `agent_runs`, `audit_events` | SELECT, INSERT | System worker scope | **NO** (allowed via `app_is_system()`) | Minimal redacted context only; no direct DDL/table owner access |
| Migrations & Schema DDL | `scenesteward` (schema owner) | DDL + DML | Schema owner | All DDL/DML, migrations | Global | **YES** (bypasses RLS by construction) | Never used by the application runtime |
| Seed Demo Scripts | `scenesteward` / `scenesteward_app` with `system_context` | DML | Dev seeds | INSERT | Dev only | Evaluated in dev | Synthetic test data only |

---

## 2. PostgreSQL Least-Privilege Roles

The application connects using dedicated non-owner roles configured in migration `c7a1e52b93f0_least_privilege_and_rls.py`:

1. `scenesteward_app`:
   - `NOBYPASSRLS`, `NOLOGIN` by default (login password provisioned via `scripts/db_roles.sql`).
   - Granted `SELECT, INSERT, UPDATE, DELETE` on all public tables.
   - Denied `TRUNCATE`, `DROP`, `ALTER`, or any DDL.
   - Explicitly denied access to `alembic_version`.

2. `scenesteward_readonly`:
   - `NOBYPASSRLS`, `SELECT` only on public tables.

3. `scenesteward` (Schema Owner):
   - Used exclusively for `alembic` migrations and administrative tasks.
   - Never used for HTTP request handling.

---

## 3. Transaction-Local Identity Context (`app.user_id` & `app.system`)

To prevent identity leakage across pooled database connections (such as PgBouncer or SQLAlchemy connection pools):
- Identity is established transaction-locally using `SELECT set_config('app.user_id', '<uuid>', true)`.
- The third parameter `true` ensures the setting is local to the current transaction (`SET LOCAL`) and is discarded when the transaction commits or rolls back.
- SQLAlchemy 2.0 lifecycle management:
  - An `@event.listens_for(Session, "after_begin")` listener inspects `session.info["user_id"]` and re-applies `set_config('app.user_id', ..., true)` on every transaction begun by that session.
  - A fallback contextvar `_identity_var` and `_system_var` provides process-level tracking.
  - Nested `system_context(session)` blocks are guarded with `was_system` tracking, ensuring inner context exits do not prematurely clear outer system privileges.
  - Any connection with missing identity context evaluates `app_authenticated()` to `FALSE` and sees **ZERO** project rows (deny-by-default).

---

## 4. Row Level Security Policies

RLS is enabled on all 18 project-scoped tables:
`projects`, `project_memberships`, `participants`, `participant_contact_records`, `release_documents`, `release_document_pages`, `consent_records`, `consent_choices`, `story_elements`, `proposed_uses`, `proposed_use_analyses`, `reviews`, `agent_runs`, `participant_communications`, `audit_events`, `integration_events`, `tasks`, `switch_room_links`.

### Policy Design Principles:
1. **Projects**:
   - SELECT: `app_is_member(id) OR created_by = current_user OR app_is_system()` (allows RETURNING on creation before membership flush).
   - INSERT: `app_authenticated() OR app_is_system()`.
   - UPDATE: `app_has_role(id, '{project_owner,producer,director}') OR app_is_system()`.
2. **Project Memberships**:
   - Creator can insert initial membership (`NOT app_project_has_members(project_id)`).
   - Project owner can manage subsequent memberships.
3. **Participant Contact Records**:
   - Access strictly restricted to `project_owner`, `producer`, `participant_care_lead`, or the participant's linked user ID (`app_is_participant_self`).
   - Editors, directors, viewers cannot view contact records under any circumstances.
4. **Consent Records & Choices**:
   - Project members can SELECT.
   - Insert and update restricted to authorised roles.
5. **Audit Events**:
   - Immutability: **NO UPDATE or DELETE policies exist** for `scenesteward_app`.
   - SELECT: `(project_id IS NOT NULL AND app_is_member(project_id)) OR (actor_type = 'user' AND actor_id = current_user) OR app_is_system()`.
   - INSERT: `app_authenticated() OR app_is_system()`.

---

## 5. Database Triggers (Defense-in-Depth)

Even if RLS was bypassed (e.g. by a superuser or schema owner), integrity triggers enforce immutability:
1. `trg_audit_events_no_update` & `trg_audit_events_no_delete`: Raises exception on any UPDATE or DELETE attempt on `audit_events`.
2. `trg_consent_records_guard`: Prevents modification of confirmed consent records.
3. `trg_consent_choices_guard`: Prevents modification of choices attached to confirmed consent records.

---

## 6. Verification Evidence

Direct SQL tests in `backend/tests/security/test_rls_isolation.py` prove:
1. `test_deny_by_default_without_identity`: Connection with no user ID sees 0 rows.
2. `test_cross_project_select_isolation`: User A cannot select Project B data.
3. `test_cross_project_insert_denied`: User A cannot insert into Project B.
4. `test_cross_project_update_invisible_or_denied`: User A cannot update Project B (0 rows affected).
5. `test_cross_project_delete_invisible_or_denied`: User A cannot delete Project B records (0 rows affected).
6. `test_contact_records_role_restriction`: Editor cannot read contacts; Care Lead can.
7. `test_connection_pool_context_isolation`: Pool connection reuse does not leak identity context.
8. `test_audit_events_immutability`: Mutating audit events is denied at both RLS and trigger levels.

