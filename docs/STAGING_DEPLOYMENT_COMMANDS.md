# SceneSteward — Staging Deployment Operational Runbook & Commands

**Date**: November 4, 2026  
**Auditor**: Principal DevOps Engineer & Site Reliability Specialist  
**Target Environments**: Docker Compose Staging Host & Host-Native Runner  

---

## 1. Prerequisites & Secret Preparation

Before deploying the staging stack, create `backend/.env.staging` from the template:

```powershell
# Copy the staging configuration template
Copy-Item backend/.env.staging.example backend/.env.staging
```

Populate the required secrets in `backend/.env.staging`:
- `DATABASE_IDENTITY_SECRET`: Cryptographic HMAC key (`openssl rand -hex 32`)
- `APP_ENCRYPTION_KEY`: Fernet 256-bit key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `ANTHROPIC_API_KEY`
- `SWITCH_BASE_URL`, `SWITCH_API_KEY`, `SWITCH_AGENT_ID`

---

## 2. Path A: Docker-Enabled Staging Host Deployment

Use these exact commands on any host with Docker and Docker Compose installed:

### Step 1: Validate Compose Syntax & Environment
```bash
docker compose -f docker-compose.staging.yml config
```

### Step 2: Build and Start Services
```bash
# Start database and ClamAV daemon first
docker compose -f docker-compose.staging.yml up -d db clamav

# Wait for database and ClamAV health probes to turn healthy
docker compose -f docker-compose.staging.yml ps

# Execute database schema migrations
docker compose -f docker-compose.staging.yml up --abort-on-container-exit migrate

# Start the API service and background worker
docker compose -f docker-compose.staging.yml up -d api worker
```

### Step 3: Inspect Service Health & Readiness
```bash
# Verify container states and health checks
docker compose -f docker-compose.staging.yml ps

# Tail API service logs
docker compose -f docker-compose.staging.yml logs -f api

# Query API health endpoint on host port 8001
curl -f http://localhost:8001/health
```

### Step 4: Graceful Shutdown & Maintenance
```bash
# Graceful stop of all staging services (preserves volumes)
docker compose -f docker-compose.staging.yml down

# Complete teardown including volumes (DISASTER TESTING ONLY)
docker compose -f docker-compose.staging.yml down -v
```

---

## 3. Path B: Host-Native Staging Deployment (Windows / Linux)

On hosts where Docker is not installed (e.g. running directly on host PostgreSQL 18 and Python 3.12):

### Step 1: Target Staging Environment
```powershell
# In PowerShell:
$env:SCENESTEWARD_ENV_FILE = "backend/.env.staging"
$env:PYTHONPATH = "backend"
```

```bash
# In Bash:
export SCENESTEWARD_ENV_FILE="backend/.env.staging"
export PYTHONPATH="backend"
```

### Step 2: Apply Database Migrations
```powershell
.\backend\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
```

### Step 3: Launch Background Outbox Worker
```powershell
Start-Process .\backend\.venv\Scripts\python.exe -ArgumentList "backend/scripts/switch_retry.py"
```

### Step 4: Launch Web API Service
```powershell
.\backend\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8001 --workers 2 --proxy-headers
```

### Step 5: Execute Provider Verification Suite
```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/verify_staging_all.py
```

---

## 4. Disaster Recovery & Backup Verification Commands

```powershell
# Snapshot staging database to compressed archive
pg_dump -h 127.0.0.1 -p 5433 -U scenesteward -d scenesteward_staging -Fc -f var/backups/staging_snapshot.dump

# Test isolated restoration into disposable database
createdb -h 127.0.0.1 -p 5433 -U postgres scenesteward_staging_restore_test
pg_restore -h 127.0.0.1 -p 5433 -U postgres -d scenesteward_staging_restore_test --clean --if-exists var/backups/staging_snapshot.dump
dropdb -h 127.0.0.1 -p 5433 -U postgres scenesteward_staging_restore_test
```

