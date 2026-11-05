# 05. PostgreSQL RLS and Privilege Audit

## Database Security Architecture

SceneSteward implements an in-depth defense model at the database tier using PostgreSQL Row-Level Security (RLS) and strict role separation.

### Role Separation & Permissions Matrix
1. **Schema Owner (`scenesteward`)**:
   - Owns all tables, schemas, views, and functions.
   - Bypasses RLS by construction in PostgreSQL.
   - Used strictly for Alembic migration execution (`alembic upgrade head`) and test suite initialization/truncation.
   - Prohibited from use in application runtime or HTTP request servicing.

2. **Application Runtime Role (`scenesteward_app`)**:
   - `NOBYPASSRLS`, `NOSUPERUSER`, `NOCREATEROLE`, `NOCREATEDB`.
   - Granted `CONNECT` on database and `USAGE` on `public` and `private` schemas.
   - Granted `SELECT, INSERT, UPDATE, DELETE` on application tables in `public`.
   - Granted **ONLY `SELECT`** on `private.app_secrets`.
   - Explicitly denied `INSERT`, `UPDATE`, `DELETE`, or `TRUNCATE` on `private.app_secrets`.

### Row-Level Security (RLS) Enforcement
- Every table holding tenant, user, or project data has `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` enabled.
- The `FORCE ROW LEVEL SECURITY` directive ensures that table owners or any future table alterations cannot bypass RLS inadvertently.
- Query isolation is mediated through `app_current_user_id()`:
  - If `app.system = 'on'` AND `app.system_sig` matches `sha256('system:on:' || secret)`, system background workers (outbox worker, sweeping jobs) are granted access.
  - If `app.user_id` is set AND `app.user_sig` matches `sha256(user_id || ':' || secret)`, access is granted only to rows associated with active project memberships of that authenticated user.
  - If signatures are missing, tampered, or mismatched, `app_current_user_id()` returns `NULL` and RLS rejects all row access by default (deny-by-default).

### Privilege Escalation & SQL Injection Defense
- `app_current_user_id()` handles malformed or SQL-injected inputs safely: invalid UUIDs caught via `INVALID_TEXT_REPRESENTATION` fail closed and return `NULL`.
- Verified via adversarial automated tests that modifying `app.user_id` without a valid HMAC signature returns 0 visible rows.
