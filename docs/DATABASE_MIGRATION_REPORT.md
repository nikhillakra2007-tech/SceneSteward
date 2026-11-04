# SceneSteward Database Migration Report

**Date**: November 4, 2026  
**PostgreSQL Version**: 18.6  
**Alembic Head**: `e1f2a3b4c5d6`

---

## 1. Alembic Migration History & Ledger

| Revision ID | Description | Created At | Down Revision | Tables Modified / Created |
|---|---|---|---|---|
| `0001_initial` | Initial database schema | 2026-11-04 | None | 19 core tables, foreign keys, unique indexes |
| `0002_triggers` | PostgreSQL domain integrity triggers | 2026-11-04 | `0001_initial` | Triggers for confirmed consent immutability, supersession, audit tamper-proofing |
| `c7a1e52b93f0` | Least-privilege roles, RLS policies, outbox project_id | 2026-11-04 | `0002_triggers` | Grants to `scenesteward_app`, RLS on 18 tables, 69 policies, `integration_events.project_id` |
| `e1f2a3b4c5d6` | Cryptographic trust boundary & composite referential integrity | 2026-11-04 | `c7a1e52b93f0` | `private.app_secrets`, HMAC signature verification functions, composite FK constraints |

---

## 2. Migration Validation & Reversibility Testing

1. **Forward Migration**:
   - `alembic upgrade head` executes cleanly and idempotently across all 4 revisions on both `scenesteward` and `scenesteward_test`.
2. **Backward Rollback Testing**:
   - `alembic downgrade -1` from `e1f2a3b4c5d6` to `c7a1e52b93f0`:
     - Safely drops composite foreign keys (`fk_proposed_uses_participant_project`, etc.).
     - Drops composite unique constraints.
     - Restores standard GUC lookup functions.
     - Drops schema `private` and table `private.app_secrets`.
   - `alembic upgrade head` re-applies `e1f2a3b4c5d6` cleanly without schema drift.
3. **Automated Migration Tests**:
   - `tests/integration/test_migrations.py` runs 4 comprehensive verification tests:
     - `test_migrations_upgrade_head_clean`: Verifies schema builds cleanly from base.
     - `test_downgrade_and_reupgrade`: Verifies downgrade and re-upgrade cycles maintain integrity.
     - `test_schema_matches_models`: Confirms zero schema drift between SQLAlchemy models and PostgreSQL catalog.
     - `test_all_tables_have_primary_keys`: Verifies explicit primary keys across all relations.

---

## 3. Least-Privilege Role Separation Architecture

- **Schema Owner & Migration Role (`scenesteward`)**:
  - Owns all schemas (`public`, `private`), tables, triggers, sequences, and functions.
  - Exclusively used for executing Alembic migrations and disaster recovery restore routines.
- **Runtime Application Role (`scenesteward_app`)**:
  - `NOBYPASSRLS`, non-superuser.
  - Granted DML only (`SELECT, INSERT, UPDATE, DELETE`) on `public` tables and sequences.
  - Denied DDL, truncation, schema changes, and denied access to `private` schema.
  - Identity constrained by HMAC-SHA256 signature verification.
- **Read-Only Reporting Role (`scenesteward_readonly`)**:
  - `NOBYPASSRLS`, non-superuser.
  - Granted `SELECT` only on `public` tables.
  - Subject to RLS policies.
