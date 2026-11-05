# SceneSteward — Staging Troubleshooting & Operational Triage Guide

## 1. Quick Diagnostic Checklist

When investigating an issue in the staging environment, perform these triage steps first:

```bash
# 1. Check container health status
docker compose -f docker-compose.staging.yml ps

# 2. Inspect API logs for unhandled errors
docker compose -f docker-compose.staging.yml logs --tail=100 api

# 3. Query the API readiness endpoint
curl -v http://127.0.0.1:8001/health/ready

# 4. Check database connectivity and active connections
docker compose -f docker-compose.staging.yml exec db psql -U scenesteward_staging -d scenesteward_staging -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## 2. Common Staging Issues & Solutions

### 2.1 Database Trust Handshake Failure
- **Symptom**: API container fails healthcheck or startup with `RuntimeError: Database trust handshake failed`.
- **Root Cause**: The HMAC identity secret stored in `private.app_secrets` does not match the application's `DATABASE_IDENTITY_SECRET` environment variable.
- **Resolution**:
  1. Verify the value of `DATABASE_IDENTITY_SECRET` in `backend/.env.staging`.
  2. Re-synchronize the secret by re-running the migration container:
     ```bash
     docker compose -f docker-compose.staging.yml up migrate
     ```
  3. Or run the synchronization script directly connecting as schema owner:
     ```bash
     python scripts/rotate_identity_secret.py --force
     ```

### 2.2 Redis Connection Drop / In-Memory Fallback
- **Symptom**: Rate limiter logs `Redis rate limiter unavailable; using in-memory limiter`.
- **Root Cause**: Redis container is restarting, port 6379 is unreachable, or `REDIS_PASSWORD` is mismatched.
- **Resolution**:
  1. Check Redis container health:
     ```bash
     docker compose -f docker-compose.staging.yml exec redis redis-cli -a "$REDIS_PASSWORD" ping
     ```
  2. The application will continue operating uninterrupted using thread-safe local in-memory rate limiting.
  3. Once Redis is restored, the client automatically reconnects on subsequent requests.

### 2.3 ClamAV Daemon Startup Delay
- **Symptom**: API container healthcheck reports ClamAV error during initial bootstrap.
- **Root Cause**: ClamAV signature database initialization can take 45–60 seconds on initial cold pull.
- **Resolution**:
  1. The staging compose configuration specifies `start_period: 60s` for ClamAV and `retries: 15`.
  2. Inspect ClamAV logs:
     ```bash
     docker compose -f docker-compose.staging.yml logs -f clamav
     ```
  3. Wait for `SelfCheck: Database status OK` before launching the API container.

### 2.4 Frontend CORS Rejection
- **Symptom**: Browser console displays `Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource`.
- **Root Cause**: `FRONTEND_ORIGIN` in the backend does not match the frontend port or hostname (e.g. `http://localhost:3001`).
- **Resolution**:
  1. Update `FRONTEND_ORIGIN` in `backend/.env.staging` (or `docker-compose.staging.yml` environment block) to include the frontend URL.
  2. Restart the API service:
     ```bash
     docker compose -f docker-compose.staging.yml restart api
     ```

### 2.5 Migration Version Conflict
- **Symptom**: `migrate` container logs `alembic.util.exc.CommandError: Can't locate revision identified by '...'`.
- **Root Cause**: The staging database contains a version number not present in the current codebase's `alembic/versions`.
- **Resolution**:
  1. Verify head revision in the repository:
     ```bash
     alembic -c backend/alembic.ini heads
     ```
  2. Connect to the database as `scenesteward_staging` and inspect `alembic_version`:
     ```bash
     docker compose -f docker-compose.staging.yml exec db psql -U scenesteward_staging -d scenesteward_staging -c "SELECT version_num FROM alembic_version;"
     ```
  3. If testing migration rollbacks, downgrade to head base:
     ```bash
     docker compose -f docker-compose.staging.yml exec migrate alembic -c alembic.ini downgrade -1
     ```

---

## 3. Log Inspection & Triage Commands

| Diagnostic Task | Command |
| :--- | :--- |
| **Follow API Logs** | `docker compose -f docker-compose.staging.yml logs -f api` |
| **Follow Worker Logs**| `docker compose -f docker-compose.staging.yml logs -f worker` |
| **Inspect ClamAV Activity** | `docker compose -f docker-compose.staging.yml logs -f clamav` |
| **Inspect Redis Memory** | `docker compose -f docker-compose.staging.yml exec redis redis-cli -a "$REDIS_PASSWORD" info memory` |
| **Test Raw Antivirus Scan** | `docker compose -f docker-compose.staging.yml exec clamav clamdscan /srv/scenesteward` |
| **Check Active DB Locks** | `docker compose -f docker-compose.staging.yml exec db psql -U scenesteward_staging -d scenesteward_staging -c "SELECT * FROM pg_locks WHERE NOT granted;"` |
