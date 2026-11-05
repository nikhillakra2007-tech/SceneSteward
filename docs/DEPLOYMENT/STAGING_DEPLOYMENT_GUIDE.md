# SceneSteward — Staging Deployment Guide

## 1. Overview & Purpose

The SceneSteward staging environment provides a high-fidelity, production-mirrored deployment for validating end-to-end documentary consent workflows, cryptographic trust boundaries, background processing, and frontend interactions prior to production release.

Staging strictly isolates data, storage, and secrets from both local test environments and live production systems:
- Dedicated PostgreSQL database (`scenesteward_staging`) with Row Level Security (RLS) and HMAC-SHA256 identity verification.
- Dedicated Redis 7 instance for distributed rate limiting and state coordination.
- ClamAV 1.4 antivirus daemon enforcing fail-closed malware inspection on uploaded release forms.
- Next.js 14 production build running as an unprivileged container.
- Uvicorn/FastAPI runtime running with least-privilege database role (`scenesteward_app`).
- Transactional outbox worker executing asynchronous Switch coordination and retry loops.

---

## 2. Architecture & Service Topology

```
                          [ Internet / Browser ]
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │   Frontend Service (Next.js 14 Production)            │
       │   Port: 3001:3000 | Container: scenesteward-staging-ui │
       └────────────────────────────┬───────────────────────────┘
                                    │ NEXT_PUBLIC_API_URL
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │   FastAPI Web API Service (Uvicorn 2 Workers)          │
       │   Port: 8001:8000 | Container: scenesteward-staging-api│
       └─────┬──────────────┬──────────────┬──────────────┬─────┘
             │              │              │              │
             ▼              ▼              ▼              ▼
     ┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
     │PostgreSQL 16 ││   Redis 7    ││ ClamAV 1.4   ││Switch Worker │
     │Port: 5433    ││Port: 6380    ││Port: 3310    ││Outbox Retry  │
     │RLS + HMAC    ││Rate Limiting ││Antivirus Gate││Loop          │
     └──────────────┘└──────────────┘└──────────────┘└──────────────┘
```

| Service | Container Name | Image / Context | Port Binding | Healthcheck |
| :--- | :--- | :--- | :--- | :--- |
| **db** | `scenesteward-staging-db` | `postgres:16-alpine` | `127.0.0.1:5433:5432` | `pg_isready -U $POSTGRES_USER` |
| **redis** | `scenesteward-staging-redis` | `redis:7-alpine` | `127.0.0.1:6380:6379` | `redis-cli ping` |
| **clamav** | `scenesteward-staging-clamav` | `clamav/clamav:1.4` | `127.0.0.1:3310:3310` | `clamdscan /dev/null` |
| **migrate**| `scenesteward-staging-migrate`| `backend/Dockerfile` | N/A (One-off) | Runs `run_migrations.py` |
| **api** | `scenesteward-staging-api` | `backend/Dockerfile` | `0.0.0.0:8001:8000` | HTTP GET `/health/ready` |
| **worker** | `scenesteward-staging-worker` | `backend/Dockerfile` | N/A | `switch_retry.py --check-health` |
| **frontend**| `scenesteward-staging-frontend`| `frontend/Dockerfile` | `0.0.0.0:3001:3000` | `wget -qO- http://127.0.0.1:3000/` |

---

## 3. Prerequisites

Before launching the staging stack, ensure the following tools are available on the deployment host:
1. **Docker Engine & Docker Compose**: Docker Engine v24+ and Docker Compose v2.20+.
2. **OpenSSL**: For generating staging secrets and encryption keys.
3. **Python 3.12+**: For running operational scripts and verification tests.
4. **Node.js 20+ & npm**: For frontend package building and verification.

---

## 4. Staging Configuration Setup

1. Copy the staging environment configuration template:
   ```bash
   cp backend/.env.staging.example backend/.env.staging
   ```

2. Generate required cryptographic secrets:
   ```bash
   # 32-byte hex for database identity HMAC trust boundary
   openssl rand -hex 32

   # 256-bit Fernet key for field-level PII encryption
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

   # Strong passwords for database roles
   openssl rand -base64 24
   ```

3. Export secrets into the current shell or update `backend/.env.staging` (ensure `.env.staging` permissions are `600` and NEVER committed to Git).

---

## 5. Deployment Step-by-Step

### Step 5.1: Build Images
Build the container images for backend and frontend:
```bash
docker compose -f docker-compose.staging.yml build
```

### Step 5.2: Launch Database & Core Dependencies
Start the backing services and verify their health status:
```bash
docker compose -f docker-compose.staging.yml up -d db redis clamav
```
Verify health:
```bash
docker compose -f docker-compose.staging.yml ps
```

### Step 5.3: Run Database Migrations
Execute the migration container using the privileged schema owner role:
```bash
docker compose -f docker-compose.staging.yml up migrate
```
The migration container applies all Alembic revisions up to head (`e1f2a3b4c5d6`), synchronizes the private HMAC identity secret into `private.app_secrets`, grants runtime privileges to `scenesteward_app`, and exits cleanly with code 0.

### Step 5.4: Start Web API, Background Worker, and Frontend
```bash
docker compose -f docker-compose.staging.yml up -d api worker frontend
```

### Step 5.5: Validate Service Health
Run health checks against the staging endpoints:
```bash
# 1. API Liveness Probe
curl -f http://127.0.0.1:8001/health/live

# 2. API Readiness & Dependency Probe (Database, Redis, ClamAV)
curl -f http://127.0.0.1:8001/health/ready

# 3. Frontend HTTP Readiness Probe
curl -f http://127.0.0.1:3001/
```

---

## 6. Seed Accounts & Identity Switching

In the staging environment, the application supports rapid identity switching and interactive authentication:

| Persona | Role | Email | Use Case |
| :--- | :--- | :--- | :--- |
| **Elena Rostova** | Director / Project Owner | `director.elena@scenesteward.example.com` | Project initialization, story elements, review decisions |
| **Claire Care** | Participant Care Lead | `claire@example.com` | Consent verification, care tasks, withdrawal triage |
| **Marcus Vance** | Producer | `marcus@example.com` | Proposed uses, distribution scheduling, approvals |
| **Elena Legal** | Legal Counsel | `elena@example.com` | Release form validation, policy compliance review |

Users can authenticate via the Next.js header using either:
1. **Quick Dev Buttons**: One-click authentication as Director or Care Lead.
2. **Custom / Switch Modal**: Dialog allowing custom full name, custom email, and instant role switching.

---

## 7. Teardown & Maintenance

To safely stop the staging stack without data loss:
```bash
docker compose -f docker-compose.staging.yml stop
```

To tear down containers and networks while preserving database and storage volumes:
```bash
docker compose -f docker-compose.staging.yml down
```

To perform a complete clean-slate reset (destroys database, redis, and storage volumes):
```bash
docker compose -f docker-compose.staging.yml down -v
```
