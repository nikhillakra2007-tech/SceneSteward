# SceneSteward — Scope & Inspected Commits

## 1. Inspection Baseline

- **Repository**: `https://github.com/nikhillakra2007-tech/SceneSteward`
- **Initial Baseline Commit**: `f3da8dd36b6db79867ec7e29463ea92324031b18` (merged PR #27)
- **Branch**: `security/consolidated-trust-verification`
- **Target Branch**: `main`

## 2. Scope of Audit

The audit encompasses all source files, database schemas, migration definitions, scripts, workflows, and container configurations:

1. **Database & Migrations**:
   - `backend/migrations/versions/c7a1e52b93f0_security_hardening_rls_and_distributed_rate_limiting.py`
   - `backend/migrations/versions/e1f2a3b4c5d6_identity_trust_boundary_and_composite_integrity.py`
   - `backend/migrations/env.py`
   - `backend/alembic.ini`
   - Database roles: `postgres`, `scenesteward`, `scenesteward_app`, `scenesteward_readonly`

2. **Core Backend & Application Logic**:
   - `backend/app/core/config.py`
   - `backend/app/core/database.py`
   - `backend/app/core/lifecycle_guards.py`
   - `backend/app/core/security.py`
   - `backend/app/main.py`
   - `backend/app/api/dependencies.py`
   - `backend/app/services/consent_service.py`
   - `backend/app/services/consent_comparison.py`
   - `backend/app/services/communications.py`
   - `backend/app/services/audit.py`
   - `backend/app/services/reviews.py`

3. **Operational Utilities & Maintenance Scripts**:
   - `backend/scripts/rotate_identity_secret.py`
   - `backend/scripts/verify_documentary_lifecycle.py`
   - `backend/scripts/restore_database.py`
   - `backend/scripts/seed_demo.py`
   - `backend/scripts/verify_isolated_restore.py`

4. **CI/CD & Container Configurations**:
   - `.github/workflows/ci.yml`
   - `docker-compose.staging.yml`
   - `Dockerfile`
   - `backend/.env.staging.example`

5. **Test Harness & Test Suites**:
   - `backend/tests/conftest.py`
   - `backend/tests/security/test_ethical_consent_invariants.py`
   - `backend/tests/security/test_lifecycle_guards.py`
   - `backend/tests/security/test_rbac.py`
   - `backend/tests/security/test_rls_isolation.py`
   - `backend/tests/security/test_secret_lifecycle.py`
   - `backend/tests/security/test_trust_boundary.py`
