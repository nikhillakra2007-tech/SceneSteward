# SceneSteward — Production Deployment & Operations Guide

**Document Version:** 1.0.0  
**Status:** Active / Production Ready  
**Date:** 2026-11-04  

---

## 1. System Requirements

- **Python Runtime:** Python 3.12+ (64-bit).
- **Database:** PostgreSQL 18 with Row Level Security (RLS) and triggers enabled.
- **Container Runtime:** Docker 24+ / containerd / Podman (OCI compliant).
- **Memory & CPU:** Minimum 1 vCPU, 1 GB RAM for API worker. Recommended 2 vCPU, 4 GB RAM for production under sustained load.
- **Storage:** Minimum 10 GB persistent storage for document release files and PostgreSQL data directory.

---

## 2. Security Configuration & Least-Privilege Architecture

SceneSteward separates database credentials into two distinct roles:

1. **Schema Owner / Migration Administrator (`scenesteward`):**
   - Holds table ownership and `BYPASSRLS`.
   - Used ONLY during CI/CD or init-container migration execution (`alembic upgrade head`).
   - Injected via `MIGRATION_DATABASE_URL`.
   - NEVER used by the running web application.

2. **Application Runtime Role (`scenesteward_app`):**
   - Granted ONLY `SELECT, INSERT, UPDATE, DELETE` on application tables.
   - Flagged with `NOBYPASSRLS`.
   - Every transaction enforces PostgreSQL RLS via transaction-local session config:
     ```sql
     SELECT set_config('app.user_id', '<uuid>', true);
     ```
   - Injected via `DATABASE_URL`.

### Database Role Initialization
Run before first deployment:
```bash
psql -U postgres -d scenesteward -f backend/scripts/db_roles.sql
```

---

## 3. Environment Variable Specification

### 3.1 Required Production Variables
```bash
APP_ENV=production
DATABASE_URL=postgresql+psycopg://scenesteward_app:<runtime-password>@db.internal:5432/scenesteward
MIGRATION_DATABASE_URL=postgresql+psycopg://scenesteward:<owner-password>@db.internal:5432/scenesteward
AUTH_PROVIDER=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-jwt-token>
APP_ENCRYPTION_KEY=<base64-32-byte-fernet-key>
FRONTEND_ORIGIN=https://app.scenesteward.com
```

### 3.2 Optional / Integration Variables
```bash
# Antivirus Scanner (clamav | mock | disabled)
ANTIVIRUS_PROVIDER=clamav
CLAMAV_HOST=clamav.internal
CLAMAV_PORT=3310
ANTIVIRUS_FAIL_CLOSED=true

# Private Document Storage (supabase | local)
STORAGE_PROVIDER=supabase
STORAGE_BUCKET=scenesteward-private
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

# Switch Agent Orchestration Adapter (http | test)
SWITCH_ADAPTER=http
SWITCH_BASE_URL=https://switch.internal:8000
SWITCH_API_KEY=<switch-agent-api-key>
SWITCH_AGENT_ID=scenesteward-agent-v1
SWITCH_WEBHOOK_SECRET=<hmac-webhook-secret>

# Anthropic Claude Integration (anthropic | offline)
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-sonnet-4-5

# Operational Metrics
METRICS_ENABLED=true
```

---

## 4. Deployment Workflows

### 4.1 Step 1: Database Migration Execution
Migrations must run as an isolated one-off task prior to container boot. Never allow the web application to execute auto-migrations at startup.

```bash
docker run --rm \
  -e DATABASE_URL="$MIGRATION_DATABASE_URL" \
  scenesteward-backend:latest \
  alembic -c alembic.ini upgrade head
```

### 4.2 Step 2: Web Application Deployment
Launch the application container with runtime credentials:

```bash
docker run -d \
  --name scenesteward-api \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file /etc/scenesteward/production.env \
  scenesteward-backend:latest
```

The Dockerfile executes under a dedicated non-root user (`scenesteward`, UID 10001):
```dockerfile
USER scenesteward
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

### 4.3 Step 3: Switch Delivery Retry Sweeper Daemon
In multi-node production setups, run `scripts/switch_retry.py` as a periodic cron or background worker. Thanks to `FOR UPDATE SKIP LOCKED`, multiple sweeper processes can run simultaneously without contention:

```bash
# Periodic cron every 2 minutes:
*/2 * * * * cd /srv/scenesteward/backend && python -m scripts.switch_retry >> /var/log/switch_retry.log 2>&1
```

---

## 5. Health Monitoring & Observability

### 5.1 Health Endpoints
- `GET /health`: Liveness probe (returns HTTP 200 `{"status": "ok"}`).
- `GET /health/ready`: Readiness probe (checks PostgreSQL connection, returns HTTP 200 or 503).
- `GET /api/v1/integrations/status`: Detailed integration status breakdown.
- `GET /api/v1/metrics`: Operational metrics (request volume, average latency, database connection pool stats).
- `GET /api/v1/metrics?format=prometheus`: Prometheus scrape format.

### 5.2 Structured Audit Logging
All security-sensitive operations generate structured JSON logs and database rows in `audit_events`.
Logs include:
- `ts`: ISO 8601 UTC timestamp.
- `level`: Log level (`INFO`, `WARNING`, `ERROR`).
- `request_id`: Tracing UUID.
- `correlation_id`: Cross-service workflow tracking UUID.
- `endpoint`: HTTP request path.
- `status`: HTTP response status code.
- `duration_ms`: Execution latency in milliseconds.

