# SceneSteward — Staging Environment Architecture & Provisioning Guide

**Date**: November 4, 2026  
**Auditor / Engineer**: Principal DevOps Engineer & PostgreSQL Reliability Engineer  
**Environment Target**: Isolated Staging Deployment  
**Standard**: Reproducible, Isolated, Multi-Container & Host-Native Support  

---

## 1. Overview & Architecture

The SceneSteward staging environment is architected to mirror production invariants while running in full isolation from development and production environments.

### System Topography
```
                           +------------------------+
                           |  External Staging IdP  |
                           |   (Supabase Auth JWKS) |
                           +-----------+------------+
                                       | RS256/ES256
                                       v
+------------------+         +-------------------+         +---------------------+
|  Documentary     | HTTPS   | SceneSteward API  | ClamAV  | ClamAV TCP Daemon   |
|  Staging Clients +-------->| FastAPI (Port 8001)+------->| Port 3310 (INSTREAM)|
+------------------+         +---------+---------+         +---------------------+
                                       |
                     +-----------------+-----------------+
                     |                                   |
                     v                                   v
          +--------------------+               +--------------------+
          | PostgreSQL 18 DB   |               | Background Worker  |
          | Port 5433 (Staging)|<--------------+ switch_retry.py    |
          | 21 Tables, 69 RLS  |               +---------+----------+
          +--------------------+                         |
                     |                                   | Outbox / REST
                     v                                   v
          +--------------------+               +--------------------+
          | Supabase Storage   |               | Agent Switch Host  |
          | Private S3 Bucket  |               | Collaboration SSE  |
          +--------------------+               +--------------------+
```

---

## 2. Infrastructure Services

The staging stack is specified in `docker-compose.staging.yml`:

| Service Name | Container / Image | Internal Port | Host Port | Role & Constraints |
|:---|:---|:---:|:---:|:---|
| **`db`** | `postgres:18-alpine` | 5432 | 5433 | Dedicated staging database `scenesteward_staging`. Persistent volume `scenesteward-staging-pgdata`. |
| **`migrate`** | `scenesteward:staging` | — | — | One-off migration container. Executes `alembic upgrade head` under schema owner. |
| **`clamav`** | `clamav/clamav:latest` | 3310 | 3310 | Real ClamAV antivirus daemon over TCP INSTREAM protocol. Volume `scenesteward-staging-clamav`. |
| **`api`** | `scenesteward:staging` | 8000 | 8001 | FastAPI application running under non-root UID 10001 (`scenesteward`). Healthcheck at `/health`. |
| **`worker`** | `scenesteward:staging` | — | — | Outbox event delivery & Switch retry daemon. Runs `scripts/switch_retry.py`. |

---

## 3. Configuration & Secret Management

### Staging Environment File: `backend/.env.staging`
To run in staging mode, copy `backend/.env.staging.example` to `backend/.env.staging`:

```powershell
Copy-Item backend/.env.staging.example backend/.env.staging
```

> [!IMPORTANT]
> `backend/.env.staging` is strictly ignored by `.gitignore` (`.env.*` rule). Secrets must never be committed to Git.

### Key Environment Variables
- `APP_ENV=staging`
- `DATABASE_URL=postgresql+psycopg://scenesteward_app:PASSWORD@127.0.0.1:5433/scenesteward_staging`
- `MIGRATION_DATABASE_URL=postgresql+psycopg://scenesteward:PASSWORD@127.0.0.1:5433/scenesteward_staging`
- `DATABASE_IDENTITY_SECRET=<high-entropy-hmac-secret>`
- `AUTH_PROVIDER=supabase`
- `STORAGE_PROVIDER=supabase`
- `AI_PROVIDER=anthropic`
- `SWITCH_ADAPTER=http`
- `ANTIVIRUS_PROVIDER=clamav`

---

## 4. Provisioning Instructions

### Option A: Docker Compose Staging Stack
```powershell
# 1. Build and start staging services
docker compose -f docker-compose.staging.yml up -d --build

# 2. Check service status
docker compose -f docker-compose.staging.yml ps

# 3. View logs
docker compose -f docker-compose.staging.yml logs -f api
```

### Option B: Host-Native Staging (Windows / Linux)
```powershell
# 1. Set environment variable to target staging
$env:SCENESTEWARD_ENV_FILE = "backend/.env.staging"
$env:PYTHONPATH = "backend"

# 2. Run database migrations
.\backend\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head

# 3. Launch background worker
Start-Process .\backend\.venv\Scripts\python.exe -ArgumentList "backend/scripts/switch_retry.py"

# 4. Launch API service
.\backend\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8001 --workers 2
```

---

## 5. Staging Health & Verification Commands

```powershell
# Run the automated provider verification suite
$env:PYTHONPATH = "backend"
.\backend\.venv\Scripts\python.exe backend/scripts/verify_staging_all.py

# Check API health endpoint
Invoke-RestMethod -Uri http://127.0.0.1:8001/health

# Check Prometheus metrics endpoint
Invoke-RestMethod -Uri http://127.0.0.1:8001/api/v1/metrics
```

