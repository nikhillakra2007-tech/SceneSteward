# SceneSteward — Infrastructure Hardening Review

**Status:** Verified & Hardened  
**Date:** 2026-11-06  
**Auditors:** DevSecOps Lead, Cloud Infrastructure Engineer  
**Scope:** Docker Topologies, Container Security, Network Isolation, Resource Limits, CI/CD Pipeline  

---

## 1. Container Security & Least Privilege

SceneSteward container images follow strict least-privilege principles:

### 1.1 Backend Container (`backend/Dockerfile`)
- Base image: `python:3.12-slim`.
- Dedicated unprivileged system user created:
  ```dockerfile
  RUN addgroup --system --gid 1001 scenesteward && \
      adduser --system --uid 1001 --ingroup scenesteward scenesteward
  ```
- Package managers and build caches cleaned in single RUN layers.
- Application executed as non-root user `scenesteward` (UID 1001).
- Ephemeral writable volumes restricted to `/srv/scenesteward/backend/var/storage`.

### 1.2 Frontend Container (`frontend/Dockerfile`)
- Multi-stage build (deps -> builder -> runner) using Node 20 Alpine.
- Dedicated unprivileged runner user `nextjs` (UID 1001) in group `nodejs`.
- Only production standalone server bundle (`.next/standalone`), public assets, and minimal node runtime included in final stage.
- Executed as unprivileged user `nextjs`.

---

## 2. Docker Compose Stacks (Staging vs Production)

Both `docker-compose.staging.yml` and `docker-compose.prod.yml` implement secure network topologies:

1. **Network Isolation:** Internal bridge network (`scenesteward-prod-net`) isolates database, Redis, and ClamAV. Only the API (`8000`) and Frontend (`3000`) expose ingress ports.
2. **Explicit Resource Limits (Production):**
   - `db`: CPU limit 2.0, Memory 2048M.
   - `redis`: CPU limit 1.0, Memory 512M.
   - `clamav`: CPU limit 2.0, Memory 2048M.
   - `api`: CPU limit 2.0, Memory 2048M.
   - `frontend`: CPU limit 1.0, Memory 1024M.
3. **One-Shot Migration Container (`migrate`):**
   - Database migrations are executed exclusively by the transient `migrate` container using the schema-owner credentials (`POSTGRES_USER`).
   - The long-running `api` and `worker` containers connect exclusively as `scenesteward_app` with restricted permissions.
4. **Active Healthchecks:** Every service specifies an active `healthcheck` with realistic intervals, timeouts, and start periods (e.g. 90s start period for ClamAV virus definitions).

---

## 3. GitHub Actions CI/CD Pipeline Hardening

The repository continuous integration pipeline (`.github/workflows/ci.yml`) enforces zero-trust security checks:

- **Permissions:** Root workflow permission restricted to `contents: read`.
- **Concurrency Control:** Automatic cancellation of redundant queued runs (`cancel-in-progress: true`).
- **Pipeline Stages:**
  1. `backend-lint-and-test`: Sets up PostgreSQL 16 container, bootstraps strict roles (`scenesteward_app`, `scenesteward_readonly`), runs Alembic migrations, runs Ruff linting, runs full 276-test Pytest suite, and executes 8-step documentary lifecycle verification.
  2. `frontend-build`: Installs dependencies via `npm ci` and compiles production Next.js build.
  3. `docker-preflight`: Validates syntax of both Staging and Production Compose configurations, tests compilation of `backend/Dockerfile`, and tests compilation of `frontend/Dockerfile`.
