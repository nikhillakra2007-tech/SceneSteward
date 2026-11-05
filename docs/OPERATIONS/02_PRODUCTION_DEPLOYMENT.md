# SceneSteward Runbook 02: Production Deployment

**Document ID:** `RB-02-PRODUCTION-DEPLOYMENT`  
**Target Environment:** Production (`APP_ENV=production`)  
**Audience:** Site Reliability Engineers, Principal Architects  

---

## 1. Overview & Architecture
The SceneSteward production stack is orchestrated via `docker-compose.prod.yml` and comprises:
- `db`: PostgreSQL 16 (Alpine) with RLS and internal networking.
- `redis`: Redis 7 (Alpine) with mandatory authentication and AOF persistence.
- `clamav`: ClamAV daemon 1.4 for streaming malware detection.
- `migrate`: Isolated ephemeral container running Alembic schema updates.
- `api`: FastAPI Python 3.12 running Uvicorn with 4 workers.
- `worker`: Transactional outbox polling daemon with exponential backoff.

No database, Redis, or ClamAV ports are exposed to the public Internet or host network. Only API port 8000 is mapped to `127.0.0.1` for reverse-proxy ingress.

---

## 2. Pre-Deployment Checklist
- [ ] Database backup executed before deployment (`python -m scripts.backup_database`).
- [ ] Production `.env.production` present and verified (`chmod 600 backend/.env.production`).
- [ ] Zero placeholder values in `.env.production`.
- [ ] `AUTH_PROVIDER=supabase` configured with production keys.
- [ ] `ANTIVIRUS_FAIL_CLOSED=true` verified.
- [ ] `APP_ENCRYPTION_KEY` valid Fernet 256-bit key.
- [ ] `DATABASE_IDENTITY_SECRET` minimum 32 chars, high entropy.

---

## 3. Step-by-Step Deployment Procedure

### Step 1: Pre-flight Verification
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml config --quiet
```

### Step 2: Build Production Containers
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml build --pull
```

### Step 3: Start Datastores, Cache & Security Daemons
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d db redis clamav
```
Wait for healthy status across all 3 daemons:
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml ps --filter "health=healthy"
```

### Step 4: Run Database Migrations to Head
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up --abort-on-container-exit migrate
```
Ensure container exits with code `0`. If migration fails, DO NOT proceed to Step 5.

### Step 5: Start API and Background Worker
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d api worker
```

---

## 4. Production Smoke Testing & Signoff

1. **Active Readiness Probe**:
   ```bash
   curl -i http://127.0.0.1:8000/health/ready
   ```
   Must return `HTTP/1.1 200 OK` with JSON:
   ```json
   {
     "status": "ok",
     "checks": {
       "database": {"status": "ok", "migration_head": "e1f2a3b4c5d6"},
       "redis": {"status": "ok"},
       "clamav": {"status": "ok"},
       "storage": {"status": "ok"}
     }
   }
   ```
2. **Database Cryptographic Handshake**:
   Check API container logs for successful startup trust handshake:
   ```bash
   docker compose --env-file backend/.env.production -f docker-compose.prod.yml logs api | grep "Database trust verification"
   ```
   *Expected output*: Zero errors.

---

## 5. Emergency Rollback Command
If critical issues occur post-deployment:
```bash
# Revert to previous image tag or rollback database
docker compose --env-file backend/.env.production -f docker-compose.prod.yml down api worker
# Follow RB-10-ROLLBACK-PROCEDURES
```
