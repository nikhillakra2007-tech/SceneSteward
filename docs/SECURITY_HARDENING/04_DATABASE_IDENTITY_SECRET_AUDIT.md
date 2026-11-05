# 04. Database Identity Secret Audit

## Threat Model & Trust Boundary
PostgreSQL Row-Level Security (RLS) in SceneSteward relies on cryptographically signed session settings:
- `app.user_id` paired with `app.user_sig = sha256(user_id || ':' || secret)`
- `app.system` paired with `app.system_sig = sha256('system:on:' || secret)`

The shared secret is stored inside a restricted schema table: `private.app_secrets (key_name TEXT PRIMARY KEY, secret_val TEXT NOT NULL)`.
The database function `app_current_user_id()` executes as `SECURITY DEFINER` with search path `pg_catalog, private` to read `private.app_secrets` and verify the HMAC/SHA-256 signature before granting row-level visibility.

## Vulnerabilities Identified in Baseline

### 1. Inadvertent Production Secret Clobbering via Alembic Migrations
- **Baseline Behavior**:
  Migration `e1f2a3b4c5d6_identity_trust_boundary_and_composite_integrity.py` executed:
  ```sql
  INSERT INTO private.app_secrets (key_name, secret_val)
  VALUES ('identity_secret', :sec)
  ON CONFLICT (key_name) DO UPDATE SET secret_val = EXCLUDED.secret_val;
  ```
- **Risk**: If an operator ran `alembic upgrade head` in staging or production with a default environment or placeholder, the active production secret was immediately wiped and replaced, causing instant service-wide authentication disruption or trust bypass.
- **Remediation**:
  Updated the migration logic to:
  1. Enforce strict production guard: If `APP_ENV=production`, verify `DATABASE_IDENTITY_SECRET` is configured and not a known placeholder (`dev_secret`, `placeholder`, `unset`), raising `RuntimeError` if violated.
  2. Use non-destructive insertion:
  ```sql
  INSERT INTO private.app_secrets (key_name, secret_val)
  VALUES ('identity_secret', :sec)
  ON CONFLICT (key_name) DO NOTHING;
  ```
  Existing production secrets remain permanently untouched by migration executions.

### 2. Test Fixture Backdoor Prevention
- **Risk**: Test fixtures executing against a real or misconfigured database could overwrite `private.app_secrets` with a test key, turning the test suite into a backdoor.
- **Remediation**:
  In `backend/tests/conftest.py`:
  - Enforced `APP_ENV != 'production'` and `APP_ENV != 'staging'`.
  - Enforced database connection URL string ends with `_test`.
  - Executed `SELECT current_database()` and asserted the actual running PostgreSQL database ends with `_test`.
  - Only in confirmed `APP_ENV=test` and `*_test` database is secret synchronization permitted.
