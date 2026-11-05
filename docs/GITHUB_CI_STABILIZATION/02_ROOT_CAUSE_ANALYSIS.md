# 02. Root Cause Analysis

## Root Cause 1: Docker Build Context Mismatch in CI
- **Failing Command**: `docker build -t scenesteward-backend:ci -f backend/Dockerfile backend`
- **Symptom**:
  ```
  #7 [3/7] COPY backend/requirements.txt backend/requirements.txt
  #7 ERROR: failed to calculate checksum of ref ...: "/backend/requirements.txt": not found
  ```
- **Technical Cause**:
  `backend/Dockerfile` specifies `COPY backend/requirements.txt backend/requirements.txt` and `COPY backend/ backend/`. The Dockerfile is designed to be built with repository root `.` as context (as documented and used in `docker-compose.staging.yml`). When `ci.yml` passed `backend` as the build context argument, the root inside the build context was the `backend/` directory itself, where files exist as `requirements.txt` rather than `backend/requirements.txt`.
- **Correction**:
  Update `.github/workflows/ci.yml` step to run `docker build -t scenesteward-backend:ci -f backend/Dockerfile .`.

## Root Cause 2: Cryptographic Identity Trust Boundary Secret Mismatch in CI
- **Failing Command**: `pytest -v backend/tests`
- **Symptom**:
  ```
  psycopg.errors.InsufficientPrivilege: new row violates row-level security policy for table "projects"
  [SQL: INSERT INTO projects ... RETURNING projects.id, ...]
  assert 500 == 201
  ```
- **Technical Cause**:
  1. PostgreSQL Migration `e1f2a3b4c5d6` creates the table `private.app_secrets` and initially inserted a hardcoded default: `'scenesteward_db_trust_secret_2026_prod_v1'`.
  2. In CI (`.github/workflows/ci.yml`), the test execution step passed `DATABASE_IDENTITY_SECRET: "ci_database_identity_secret_2026_test_only"`.
  3. However, step 8 (`Run Alembic Migrations to Head`) did NOT receive `DATABASE_IDENTITY_SECRET`, and the migration script had hardcoded the production default.
  4. At runtime during tests, Python generated session HMAC signatures using `"ci_database_identity_secret_2026_test_only"`, while PostgreSQL's `app_current_user_id()` validated against `private.app_secrets.secret_val` (`"scenesteward_db_trust_secret_2026_prod_v1"`).
  5. The HMAC signatures did not match (`v_sig <> encode(sha256((v_user || ':' || v_secret)::bytea), 'hex')`), causing `app_current_user_id()` to return `NULL`.
  6. The `projects` RLS policy `created_by = public.app_current_user_id()` evaluated to `created_by = NULL` (`FALSE`), rejecting `INSERT ... RETURNING` with `InsufficientPrivilege`.
- **Correction**:
  1. Synchronize `private.app_secrets` with `get_settings().database_identity_secret` in `backend/tests/conftest.py` fixture `_verify_schema` using the schema-owner engine `_admin_engine`.
  2. Allow migration `e1f2a3b4c5d6` to read `os.environ.get("DATABASE_IDENTITY_SECRET", ...)`.
  3. Provide `DATABASE_IDENTITY_SECRET: "ci_database_identity_secret_2026_test_only"` and explicit `DATABASE_URL` in `.github/workflows/ci.yml`.
  4. Ensure `verify_documentary_lifecycle.py` routes `DATABASE_URL` to `DATABASE_URL_TEST` and synchronizes `private.app_secrets` when run standalone.
