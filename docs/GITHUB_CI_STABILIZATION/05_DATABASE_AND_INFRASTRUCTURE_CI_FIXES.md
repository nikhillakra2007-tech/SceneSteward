# 05. Database & Infrastructure CI Fixes

## 1. GitHub Actions Workflow Configuration Updates
In `.github/workflows/ci.yml`:
1. **Docker Build Context**:
   Updated step `Test Backend Container Build` from:
   ```yaml
   docker build -t scenesteward-backend:ci -f backend/Dockerfile backend
   ```
   to:
   ```yaml
   docker build -t scenesteward-backend:ci -f backend/Dockerfile .
   ```
   This ensures the Docker daemon evaluates `COPY backend/requirements.txt` and `COPY backend/ backend/` relative to the repository root.

2. **Database Identity Secret in Migration Step**:
   Added `DATABASE_IDENTITY_SECRET: "ci_database_identity_secret_2026_test_only"` to step `Run Alembic Migrations to Head`.

3. **Explicit Database URL Mapping**:
   Explicitly passed `DATABASE_URL: "postgresql+psycopg://scenesteward_app:app_test_password@localhost:5432/scenesteward_test"` to both `Run Pytest Suite` and `Verify 8-Step Documentary Lifecycle` steps.

## 2. Docker Compose Validation
Verified `docker compose -f docker-compose.staging.yml config` passes cleanly with all services (`db`, `clamav`, `migrate`, `api`, `worker`) and build contexts resolved properly.
