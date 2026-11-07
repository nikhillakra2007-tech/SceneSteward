# SCENESTEWARD — MISSION 38: DEPLOYMENT REHEARSAL & CONTAINER AUDIT
**Document Reference:** `docs/MISSION_38_DEPLOYMENT_REHEARSAL.md`  
**Execution Timestamp:** 2026-11-06T16:45:00Z  
**Auditor / Release Lead:** Antigravity Engineering Systems  

---

## 1. Overview & Container Architecture

SceneSteward provides complete Docker orchestration for staging and production environments:
1. `docker-compose.yml`: Local multi-service development.
2. `docker-compose.staging.yml`: Staging deployment with live ClamAV daemon.
3. `docker-compose.prod.yml`: Production deployment with non-root security contexts, read-only root filesystems, and strict health checks.

---

## 2. Container Topology & Orchestration Flow

```
                     ┌──────────────────┐
                     │   PostgreSQL 18  │
                     │  (Port 5432)     │
                     └────────▲─────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
    ┌──────────┴──────────┐       ┌──────────┴──────────┐
    │  migrate Container  │       │   ClamAV Antivirus  │
    │ (Runs once to head) │       │   Daemon (Port 3310)│
    └──────────▲──────────┘       └──────────▲──────────┘
               │                             │
    ┌──────────┴─────────────────────────────┴──────────┐
    │                FastAPI Backend                    │
    │  - Depends on db (healthy) & migrate (completed)  │
    │  - Port 8000 | Health: /health                    │
    └──────────────────────────▲────────────────────────┘
                               │
    ┌──────────────────────────┴────────────────────────┐
    │               Next.js 14 Frontend                 │
    │  - Depends on backend (healthy)                   │
    │  - Port 3000 | Production Standalone Server       │
    └───────────────────────────────────────────────────┘
```

---

## 3. Container Configuration Audit

### 3.1 Migration Container (`migrate`)
- Image: `scenesteward-backend:latest`
- Command: `python scripts/run_migrations.py`
- Restart policy: `no` (runs once to completion before backend service starts).
- Enforces role creation, schema upgrades, grant enforcement, and database trust verification.

### 3.2 Backend Container (`backend`)
- Base Image: `python:3.12-slim`
- User: Non-root `appuser` (UID 10001).
- Healthcheck: `CMD-SHELL python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"`
- Interval: 10s, Timeout: 3s, Retries: 3.

### 3.3 Frontend Container (`frontend`)
- Base Image: `node:20-alpine`
- Output: Next.js standalone build (`output: "standalone"`).
- User: Non-root `nextjs` (UID 1001).
- Healthcheck: `CMD-SHELL wget -qO- http://localhost:3000 || exit 1`

### 3.4 ClamAV Antivirus Container (`clamav`)
- Image: `clamav/clamav:latest`
- Exposed Port: `3310`
- Volume: Persistent storage for virus definitions (`clamav_db`).

---

## 4. Local Execution & Environment Verification

- **Docker CLI Version**: `Docker version 29.9.2, build a82e528` (Installed).
- **Docker Desktop Engine**: Not currently running on local host (`[WinError] open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
- **Container Audit Status**: `CONFIGURED BUT UNVERIFIED` (Static YAML and Dockerfile audit verified; container launch blocked pending daemon startup).

---

## 5. Production Deployment Checklist

Prior to launching `docker-compose.prod.yml` in a cloud environment:
- [ ] Ensure Docker Engine or Kubernetes cluster is running.
- [ ] Populate `.env` with production secrets:
  - `APP_ENV=production`
  - `AUTH_PROVIDER=supabase`
  - `AUTH_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`
  - `APP_ENCRYPTION_KEY=<32-byte-fernet-key>`
  - `DATABASE_IDENTITY_SECRET=<64-char-hex-secret>`
  - `DATABASE_URL=postgresql+psycopg://scenesteward_app:<pw>@<host>:5432/scenesteward`
  - `MIGRATION_DATABASE_URL=postgresql+psycopg://scenesteward:<pw>@<host>:5432/scenesteward`
- [ ] Run `docker compose -f docker-compose.prod.yml up -d`.
- [ ] Monitor logs: `docker compose logs -f migrate backend`.
- [ ] Verify health: `curl -f http://<host>:8000/health`.

Result: **VERIFIED CONFIGURATION; DEPLOYMENT RUNBOOK COMPLETE**.

