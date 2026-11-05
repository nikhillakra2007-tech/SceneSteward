# SceneSteward Runbook 01: Staging Deployment

**Document ID:** `RB-01-STAGING-DEPLOYMENT`  
**Target Environment:** Staging (`APP_ENV=staging`)  
**Audience:** DevOps Engineers, Release Leads  

---

## 1. Overview & Objective
This runbook guides engineers through deploying and validating the SceneSteward staging stack (`docker-compose.staging.yml`). The staging environment provides an isolated pre-production environment with real database constraints, Row Level Security (RLS), ClamAV daemon antivirus scanning, transactional outbox worker, and Supabase Auth.

---

## 2. Prerequisites
1. Docker Engine 24+ and Docker Compose v2.20+.
2. Valid staging configuration file: `backend/.env.staging` (copied from `backend/.env.staging.example`).
3. External connectivity to Supabase Auth (`SUPABASE_URL`, `SUPABASE_ANON_KEY`).
4. Staging network ports free: `5433` (Postgres, bound to `127.0.0.1`), `3310` (ClamAV, bound to `127.0.0.1`), `8001` (API).

---

## 3. Configuration Setup
Ensure all mandatory environment variables are populated in `backend/.env.staging`:

```bash
# Verify no placeholder strings exist
grep -E "CHANGE_ME|GENERATE" backend/.env.staging && echo "ERROR: Placeholders remain!" || echo "Config ready."
```

Mandatory variables:
- `POSTGRES_PASSWORD`: Strong password for `scenesteward_staging`.
- `DATABASE_IDENTITY_SECRET`: 64-char hex string (`openssl rand -hex 32`).
- `APP_ENCRYPTION_KEY`: 32-byte url-safe base64 Fernet key.
- `AUTH_PROVIDER`: Must be `supabase`.
- `SUPABASE_URL` and `SUPABASE_ANON_KEY`.

---

## 4. Deployment Steps

### Step 1: Pre-flight Configuration Validation
Validate the compose topology:
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml config --quiet
```

### Step 2: Build Images
Build the backend container image:
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml build --no-cache
```

### Step 3: Boot Datastores & ClamAV
Start the database and antivirus daemon first:
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml up -d db clamav
```
Wait for health status:
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml ps
```

### Step 4: Execute Database Migrations
Run the one-shot migration runner:
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml up --abort-on-container-exit migrate
```
Verify exit code is `0`.

### Step 5: Boot API and Background Worker
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml up -d api worker
```

---

## 5. Post-Deployment Verification

1. **Check Service Status**:
   ```bash
   docker compose --env-file backend/.env.staging -f docker-compose.staging.yml ps
   ```
2. **Verify Liveness and Readiness**:
   ```bash
   curl -s http://127.0.0.1:8001/health | jq .
   curl -s http://127.0.0.1:8001/health/ready | jq .
   ```
   *Expected response*: HTTP 200, `status: "ok"`, `checks.database.status: "ok"`.
3. **Verify Worker Logs**:
   ```bash
   docker compose --env-file backend/.env.staging -f docker-compose.staging.yml logs --tail=50 worker
   ```

---

## 6. Teardown (Non-Destructive)
To stop the staging stack without deleting persistent data:
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml stop
```
