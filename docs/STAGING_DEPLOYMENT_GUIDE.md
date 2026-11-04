# SceneSteward — Staging Deployment Guide

**Target Environment**: Staging / Pre-Production Evaluation  
**Platform**: Linux / Windows Container / Bare-Metal (Python 3.12+, PostgreSQL 18.6)  
**Security Standard**: Least Privilege Runtime (`NOBYPASSRLS`), Cryptographic HMAC Identity Gating, Envelope Encryption for PII

---

## 1. System Requirements & Architecture

SceneSteward requires:
1. **PostgreSQL 18.6+**: With two distinct roles:
   - `scenesteward`: Database and schema owner (used strictly for running migrations and disaster recovery).
   - `scenesteward_app`: Runtime application role (`NOBYPASSRLS`, DML only: `SELECT, INSERT, UPDATE, DELETE` on `public` tables; no access to `private` schema).
2. **Python 3.12+**: Virtualenv with dependencies installed via `pip install -r requirements.txt`.
3. **External Staging Services** (optional for local simulation, required for live staging):
   - Supabase Auth & Storage project.
   - Anthropic API key (`claude-sonnet-4-5`).
   - Switch Core agent collaboration hub.
   - ClamAV clamd daemon (TCP port 3310).

---

## 2. Step-by-Step Staging Setup

### Step 2.1 — Environment Configuration
Copy the template configuration file:
```bash
cp backend/.env.example backend/.env
```
Populate the essential secrets in `backend/.env`:
```ini
APP_ENV=staging
DATABASE_URL=postgresql+psycopg://scenesteward_app:<APP_PW>@127.0.0.1:5432/scenesteward
DATABASE_URL_ADMIN=postgresql+psycopg://scenesteward:<OWNER_PW>@127.0.0.1:5432/scenesteward
MIGRATION_DATABASE_URL=postgresql+psycopg://scenesteward:<OWNER_PW>@127.0.0.1:5432/scenesteward

# Cryptographic database trust boundary secret (shared between backend and private.app_secrets)
DATABASE_IDENTITY_SECRET=<RANDOM_HEX_64>

# PII envelope encryption key
APP_ENCRYPTION_KEY=<FERNET_KEY_32_BYTES>
APP_ENCRYPTION_CURRENT_KID=primary-staging-v1
APP_ENCRYPTION_KEYS={"primary-staging-v1": "<FERNET_KEY_32_BYTES>"}
```

### Step 2.2 — Database Roles & Migrations
1. **Provision Database Roles**:
   Connect as the PostgreSQL superuser (`postgres`) and execute:
   ```bash
   psql -U postgres -d scenesteward -f backend/scripts/db_roles.sql
   ```
2. **Apply Alembic Migrations to Head (`e1f2a3b4c5d6`)**:
   ```bash
   cd backend
   .\.venv\Scripts\alembic upgrade head
   ```
3. **Verify Catalog Objects**:
   ```bash
   python scripts/inspect_catalog.py
   ```
   Confirm 21 tables, 69 RLS policies, and 4 application triggers.

### Step 2.3 — Launching the Backend API
Start the FastAPI application via Uvicorn:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```
Verify the startup probe:
```bash
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/health/ready
```

### Step 2.4 — Launching Background Sweepers
The asynchronous outbox worker handles resilient delivery to Switch without blocking user transactions:
```bash
# As a periodic cron job (every 2 minutes):
*/2 * * * * cd /opt/scenesteward/backend && ./.venv/bin/python scripts/switch_retry.py >> /var/log/switch_retry.log 2>&1

# Or run interactively:
python scripts/switch_retry.py
```

---

## 3. Connecting Real External Providers

### 3.1 Supabase Auth
In `backend/.env`:
```ini
AUTH_PROVIDER=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
AUTH_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
AUTH_AUDIENCE=authenticated
```
*Behavior*: Tokens are validated against the remote JWKS using RS256/ES256. Users signing in for the first time are JIT-provisioned into PostgreSQL with `account_status='active'`.

### 3.2 Supabase Storage
In `backend/.env`:
```ini
STORAGE_PROVIDER=supabase
STORAGE_BUCKET=scenesteward-private
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```
*Behavior*: Signed upload targets and download URLs are generated against the private Supabase bucket. Expiring URLs are never permanently stored in PostgreSQL.

### 3.3 Anthropic Claude API
In `backend/.env`:
```ini
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-sonnet-4-5
AI_TIMEOUT_SECONDS=45
```
*Behavior*: Specialist agents query Claude for structured advisory analysis. If the API is rate-limited (429) or times out, the system fails closed or falls back to rule-based heuristics without halting human review.

### 3.4 Switch Collaboration Core
In `backend/.env`:
```ini
SWITCH_ADAPTER=http
SWITCH_BASE_URL=http://<switch-core-host>:8000
SWITCH_API_KEY=<agent-api-key>
SWITCH_AGENT_ID=agent:<uuid>
```
*Behavior*: Events are committed transactionally to `integration_events` and delivered by `switch_retry.py` using `SELECT ... FOR UPDATE SKIP LOCKED`.

### 3.5 ClamAV Antivirus
In `backend/.env`:
```ini
ANTIVIRUS_PROVIDER=clamav
CLAMAV_HOST=127.0.0.1
CLAMAV_PORT=3310
ANTIVIRUS_FAIL_CLOSED=true
```
*Behavior*: Uploaded document bytes are streamed directly to ClamAV via `zINSTREAM`. Any document containing malware or failing the scan in production is discarded immediately.

---

## 4. Disaster Recovery & Backup Runbook

### Taking an Atomic Backup:
```bash
python scripts/backup_database.py
```
Outputs a compressed, SHA-256 verified custom dump (`.dump`) into `backend/var/backups/`.

### Restoring to an Isolated Target:
```bash
python scripts/restore_database.py <path-to-dump> <target-db-name>
```

### Verifying Disaster Recovery:
```bash
python scripts/verify_isolated_restore.py
```
Validates sub-second RTO, complete table restoration, trigger enforcement, RLS policy preservation, and contact data decryption.

