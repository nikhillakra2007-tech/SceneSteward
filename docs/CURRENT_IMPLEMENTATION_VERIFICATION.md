# Current Implementation Verification Report

**Date**: November 4, 2026  
**Environment**: Production Candidate Verification (Windows / PostgreSQL 18.6 / Python 3.12)  
**Repository Branch**: `main`  
**Latest Alembic Revision**: `e1f2a3b4c5d6` (Head)

---

## 1. Executive Summary

A comprehensive architectural and empirical verification of the SceneSteward backend was conducted. The system has evolved from an initial prototype with basic unit tests to an enterprise-grade, cryptographically bounded multi-tenant production candidate.

All core domain principles are strictly upheld:
- **Foundational Tenant**: *A participant's agreement to one use must never automatically become agreement to another use. Silence is never agreement.*
- **Authoritative Source of Truth**: SceneSteward PostgreSQL 18 database with strict Row Level Security (RLS) and cryptographic HMAC trust boundary gating.
- **Role of External Systems**: Switch is an asynchronous orchestration/collaboration layer; AI agents provide advisory analyses only and cannot approve consent or make human decisions.

---

## 2. PostgreSQL Catalog & Schema Inventory

The database catalog inspection reveals a rigorously partitioned relational model:

### 2.1 Table Categorization (Total: 20 Relations)
1. **Global Identity Directory (1 table, No RLS)**:
   - `users`: Global system user accounts, authentication provider mappings, active status flags.
2. **Project-Scoped Application Tables (18 tables, Strict RLS Enforced)**:
   - `projects`: Documentary production workspaces.
   - `project_memberships`: User-to-project role assignments (`project_owner`, `producer`, `director`, `editor`, `care_lead`, `viewer`).
   - `participants`: On-screen or background participants. Encrypted PII stored via authenticated envelope encryption.
   - `story_elements`: Scenes, themes, interviews, archival segments.
   - `release_documents`: Uploaded release forms, agreements, and notes.
   - `extracted_terms`: Extracted legal clauses and provisional terms.
   - `consent_records`: Point-in-time human-confirmed consent records.
   - `consent_choices`: Granular, use-specific consent selections.
   - `proposed_uses`: Proposed editorial placements (e.g. trailer, broadcast, marketing).
   - `proposed_use_analyses`: AI and algorithmic checks against recorded consent.
   - `reviews`: Multi-stage editorial and participant care reviews.
   - `participant_communications`: Outbound messages, email/SMS logs, consent clarification requests.
   - `audit_events`: Append-only, tamper-evident audit ledger.
   - `outbox_events`: Transactional outbox for guaranteed event publishing.
   - `switch_tasks`: Switch orchestration sync state and workflow tasks.
   - `agent_runs`: Audit history of background AI analysis executions.
   - `scenes`: Granular scene metadata.
   - `scene_participants`: Many-to-many associations between scenes and participants.
3. **Internal Schema & Migration Metadata (2 relations)**:
   - `alembic_version`: Tracks migration history (`e1f2a3b4c5d6`).
   - `private.app_secrets`: Gated schema inaccessible to runtime application roles (`scenesteward_app`, `scenesteward_readonly`); stores the database trust secret for HMAC signature verification.

### 2.2 Trigger Inventory & Catalog Clarification
PostgreSQL `information_schema.triggers` and `pg_trigger` catalog queries report **180 triggers**:
- **Application Business Rule Triggers (4 custom triggers)**:
  - `trg_audit_events_no_delete`: Rejects any SQL `DELETE` on `audit_events`.
  - `trg_audit_events_no_update`: Rejects any SQL `UPDATE` on `audit_events`.
  - `trg_consent_choices_guard`: Immutability guard on confirmed consent choices.
  - `trg_consent_records_guard`: Immutability guard on confirmed consent records.
- **Internal System Triggers (176 triggers)**:
  - System-generated triggers (`RI_ConstraintTrigger_c_*`) created automatically by PostgreSQL to enforce primary key and foreign key referential integrity constraints across the 18 interlinked relational tables.

### 2.3 Row Level Security (RLS) Policy Summary
- **Total Policies**: 69 active policies across all 18 project-scoped tables.
- **Enforcement Status**: Tables have `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
- **Runtime Roles**:
  - `scenesteward_app`: `NOBYPASSRLS`. Operates under least-privilege `SELECT`, `INSERT`, `UPDATE`, `DELETE` grants.
  - `scenesteward_readonly`: `NOBYPASSRLS`. Operates under `SELECT` only grants.
  - `scenesteward`: Database and schema owner used exclusively for Alembic migrations and disaster recovery.

---

## 3. Cryptographic Database Trust Boundary (HMAC Verification)

### Problem Identified
Previously, an attacker with SQL injection or compromised application credentials could execute:
```sql
SELECT set_config('app.user_id', '<victim_id>', true);
-- or
SELECT set_config('app.system', 'on', true);
```
Because PostgreSQL allows setting arbitrary GUC variables, the database RLS policies blindly trusted `app.user_id` and `app.system`.

### Engineering Solution Implemented (`e1f2a3b4c5d6`)
1. **Dedicated Isolated Schema**: Schema `private` created with `REVOKE ALL ON SCHEMA private FROM PUBLIC, scenesteward_app, scenesteward_readonly;`.
2. **Cryptographic Proof Functions**:
   - `public.app_current_user_id()`: Reads `app.user_id` and `app.user_sig`. Computes `sha256(user_id || ':' || secret)` against `private.app_secrets`. Returns `NULL` if missing, invalid, or forged.
   - `public.app_is_system()`: Reads `app.system` and `app.system_sig`. Computes `sha256('system:on:' || secret)`. Returns `FALSE` if unverified.
3. **Application Hook Integration**:
   - SQLAlchemy `Session.after_begin` and engine `begin` listeners automatically generate and set `app.user_sig` and `app.system_sig` using the server-side `DATABASE_IDENTITY_SECRET`.

---

## 4. API Endpoints & Regression Status

- **Total API Routes**: 48 active REST endpoints under `/api/v1`.
- **Authentication**: JWT bearer token with Supabase Auth or local development secret verification.
- **Automated Test Results**:
  - `tests/agents/`: 5 passed
  - `tests/e2e/`: 3 passed (including 19-step lifecycle and "Beyond the Silence" full documentary flow)
  - `tests/integration/`: 26 passed (documents, extraction, outbox, auth, communications)
  - `tests/security/`: 18 passed (RBAC, encryption, key rotation, trust boundary HMAC verification)
  - `tests/unit/`: 46 passed
  - **Total**: **98 passed in 45.83s (100% pass rate)**.
- **Linting & Code Quality**: `ruff check .` passed with 0 errors.

