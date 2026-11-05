# SceneSteward — GitHub Actions & Container Security

## 1. GitHub Actions Security (`.github/workflows/ci.yml`)

1. **Least Privilege**:
   ```yaml
   permissions:
     contents: read
   ```
   No administrative write tokens are granted to CI jobs.
2. **Concurrency Control**:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```
   Prevents race conditions on parallel branch pushes.
3. **Separate Service Containers**:
   - PostgreSQL 16 runs with health checks (`pg_isready`).
   - Superuser credentials bootstrap runtime roles (`scenesteward_app`, `scenesteward_readonly`) with `NOBYPASSRLS`.
   - Tests run strictly as `scenesteward_app` to verify RLS enforcement.

## 2. Docker & Staging Security (`docker-compose.staging.yml`)

1. **Non-Root Execution**:
   - Application containers run under dedicated non-root users (`USER appuser`).
2. **Read-Only Root Filesystems & Capabilities**:
   - Unnecessary Linux capabilities dropped (`cap_drop: [ALL]`).
3. **Healthchecks**:
   - Periodic HTTP `/health/ready` probes verify service readiness.
4. **Environment Isolation**:
   - Database credentials and identity secrets configured via environment variables, never hardcoded in Dockerfiles.
