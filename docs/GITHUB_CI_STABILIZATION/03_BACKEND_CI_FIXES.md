# 03. Backend CI Fixes

## 1. Test Suite Database Identity Trust Synchronization
In `backend/tests/conftest.py`, added automated synchronization to fixture `_verify_schema`:
```python
    from app.core.config import get_settings
    with _admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO private.app_secrets (key_name, secret_val) "
                "VALUES ('identity_secret', :sec) "
                "ON CONFLICT (key_name) DO UPDATE SET secret_val = EXCLUDED.secret_val"
            ),
            {"sec": get_settings().database_identity_secret},
        )
```
This guarantees that whenever tests are run under any `DATABASE_IDENTITY_SECRET` environment setting, the PostgreSQL private secret store is immediately synchronized by the schema administrator connection before any test executes.

## 2. Documentary Lifecycle Verification Standalone Routing
In `backend/scripts/verify_documentary_lifecycle.py`:
- Added automatic resolution of `DATABASE_URL` from `DATABASE_URL_TEST` (or `.env`) prior to FastAPI application initialization.
- Added identity secret verification and synchronization via `DATABASE_URL_ADMIN` if available.

## 3. Migration Environment Secret Configuration
In `backend/migrations/versions/e1f2a3b4c5d6_identity_trust_boundary_and_composite_integrity.py`:
- Replaced hardcoded default string with `os.environ.get("DATABASE_IDENTITY_SECRET", "scenesteward_db_trust_secret_2026_prod_v1")` so initial migration respects environment overrides.

## 4. Local Verification
- Ran complete test suite: `backend/.venv/Scripts/python -m pytest backend/tests`
  - Output: `208 passed in 111.11s`
- Ran 8-step documentary lifecycle runner: `backend/.venv/Scripts/python backend/scripts/verify_documentary_lifecycle.py`
  - Output: `8/8 STEPS PASSED`
- Ran Ruff linter: `backend/.venv/Scripts/python -m ruff check backend`
  - Output: `All checks passed!`
