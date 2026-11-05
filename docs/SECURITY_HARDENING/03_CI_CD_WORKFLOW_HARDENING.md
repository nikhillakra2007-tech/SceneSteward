# 03. CI/CD Workflow Hardening

## Hardening Implemented

### Top-Level Least-Privilege Permissions
In `.github/workflows/ci.yml`, explicit top-level permissions were defined:
```yaml
permissions:
  contents: read
```
This guarantees:
1. `GITHUB_TOKEN` is strictly read-only by default across all matrix runners and jobs.
2. Compromise of any third-party build step or test artifact cannot lead to unauthorized commit pushes, release generation, or issue modifications.
3. Unauthenticated forks submitting pull requests cannot execute privileged operations.

### Service Container Isolation
The `backend-test` job relies on a localized PostgreSQL 16 container:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    env:
      POSTGRES_DB: scenesteward_test
      POSTGRES_USER: scenesteward
      POSTGRES_PASSWORD: ci_test_password
    ports:
      - 5432:5432
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```
- Hardened database setup script runs role separation creating `scenesteward_app` (RLS enforced non-owner) and `scenesteward` (schema owner).
- Migration runs via schema owner `DATABASE_URL_ADMIN`.
- Tests execute with restricted `scenesteward_app` credentials under RLS enforcement.

### Build and Artifact Protections
- Frontend build runs in isolated workspace `frontend/` without root environment variable bleed.
- Docker build preflight verifies multi-stage syntax and security boundaries without exposing host docker socket or credentials.
