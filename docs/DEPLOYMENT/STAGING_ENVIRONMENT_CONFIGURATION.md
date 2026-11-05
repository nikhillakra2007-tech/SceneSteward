# SceneSteward — Staging Environment Configuration Specification

## 1. Scope & Isolation Philosophy

The staging environment configuration ensures complete physical and logical isolation from both development fixtures and production systems.

### Isolation Rules
1. **Database Isolation**: The staging database is named `scenesteward_staging` and is hosted on port `5433` (external) / `5432` (internal Docker network). Under no circumstances will staging connect to `scenesteward_test` or production databases.
2. **PostgreSQL Role Separation**:
   - `scenesteward_staging`: Schema owner with DDL privileges, used exclusively by `migrate` container. Never used by runtime web API.
   - `scenesteward_app`: Runtime application user granted `SELECT`, `INSERT`, `UPDATE`, `DELETE` on application tables. Explicitly set to `NOBYPASSRLS`. Denied all access to `private.app_secrets`.
3. **Storage Bucket Isolation**: Staging documents are isolated to `scenesteward-staging-documents` bucket (or local encrypted storage mount `/srv/scenesteward/backend/var/storage`).
4. **Redis Isolation**: Staging rate-limiting counters reside in dedicated Redis database `0` protected by `REDIS_PASSWORD`.
5. **AI and External Integrations**: Configurable via adapters (offline/mock for air-gapped acceptance, live API for external qualification).

---

## 2. Configuration Variables Reference

| Variable | Description | Sensitivity | Staging Default / Example |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | Application environment identifier | Low | `staging` |
| `APP_NAME` | Service banner name | Low | `SceneSteward-Staging` |
| `API_VERSION` | Active API version prefix | Low | `v1` |
| `LOG_LEVEL` | Logging verbosity | Low | `INFO` |
| `POSTGRES_USER` | Schema owner username | Medium | `scenesteward_staging` |
| `POSTGRES_PASSWORD` | Schema owner password | High | Generated per deployment |
| `POSTGRES_DB` | PostgreSQL database name | Low | `scenesteward_staging` |
| `APP_USER` | Runtime unprivileged user | Low | `scenesteward_app` |
| `APP_PASSWORD` | Runtime user password | High | Generated per deployment |
| `DATABASE_URL` | Runtime connection string | High | `postgresql+psycopg://...` |
| `MIGRATION_DATABASE_URL` | Migration connection string | High | `postgresql+psycopg://...` |
| `DATABASE_IDENTITY_SECRET` | 32-byte HMAC identity secret | High | Generated with `openssl rand -hex 32` |
| `REDIS_PASSWORD` | Redis authentication token | High | Generated per deployment |
| `REDIS_URL` | Redis connection URL | High | `redis://:PASS@redis:6379/0` |
| `AUTH_PROVIDER` | Auth adapter (`dev` or `supabase`)| Low | `dev` (staging qualification) or `supabase` |
| `SUPABASE_URL` | Staging Supabase project URL | Medium | `https://YOUR_STAGING_PROJECT_REF.supabase.co` |
| `SUPABASE_ANON_KEY` | Staging Supabase anon key | Medium | Project anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Staging Supabase service key | High | Staging admin key |
| `AUTH_JWKS_URL` | JWKS validation URL | Low | Project JWKS endpoint |
| `AUTH_AUDIENCE` | Expected JWT audience | Low | `authenticated` |
| `STORAGE_PROVIDER` | Storage backend (`supabase`/`local`)| Low | `supabase` or `local` |
| `STORAGE_BUCKET` | Dedicated staging bucket name | Low | `scenesteward-staging-documents` |
| `SIGNED_URL_TTL_SECONDS` | Presigned upload URL TTL | Low | `600` (10 minutes) |
| `DOWNLOAD_URL_TTL_SECONDS` | Presigned download URL TTL | Low | `300` (5 minutes) |
| `MAX_UPLOAD_BYTES` | Maximum upload size | Low | `26214400` (25 MB) |
| `APP_ENCRYPTION_KEY` | Fernet 256-bit encryption key | High | Generated per deployment |
| `APP_ENCRYPTION_CURRENT_KID` | Key identifier for active key | Low | `staging-primary-v1` |
| `ANTIVIRUS_PROVIDER` | Antivirus engine | Low | `clamav` |
| `CLAMAV_HOST` | ClamAV daemon hostname | Low | `clamav` |
| `CLAMAV_PORT` | ClamAV daemon TCP port | Low | `3310` |
| `ANTIVIRUS_FAIL_CLOSED` | Reject files on scanner error | Low | `true` |
| `AI_PROVIDER` | AI engine (`anthropic`/`offline`) | Low | `anthropic` or `offline` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | High | `sk-ant-api-...` |
| `AI_MODEL` | Advisory model version | Low | `claude-sonnet-4-5` |
| `SWITCH_ADAPTER` | Switch backend (`http`/`test`) | Low | `http` or `test` |
| `SWITCH_BASE_URL` | Staging Switch coordination URL | Medium | `https://staging.switch.your-domain.com` |
| `SWITCH_API_KEY` | Staging Switch agent API key | High | Generated per deployment |
| `SWITCH_WEBHOOK_SECRET` | Inbound Switch HMAC secret | High | Generated per deployment |
| `FRONTEND_ORIGIN` | CORS allowed origin | Low | `http://localhost:3001` |
| `RATE_LIMIT_PER_MINUTE` | Distributed rate limit quota | Low | `120` |

---

## 3. Secret Generation Runbook

To configure a new staging environment instance, execute the following commands in a secure shell:

```bash
# 1. Database Passwords
STAGING_OWNER_PW=$(openssl rand -base64 24)
STAGING_APP_PW=$(openssl rand -base64 24)
STAGING_REDIS_PW=$(openssl rand -base64 24)

# 2. Database Identity Secret (HMAC-SHA256 for authenticated RLS context)
STAGING_IDENTITY_SECRET=$(openssl rand -hex 32)

# 3. Application Encryption Key (Fernet 256-bit)
STAGING_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 4. Write to backend/.env.staging
cat <<EOF > backend/.env.staging
APP_ENV=staging
APP_NAME=SceneSteward-Staging
POSTGRES_USER=scenesteward_staging
POSTGRES_PASSWORD=${STAGING_OWNER_PW}
POSTGRES_DB=scenesteward_staging
APP_USER=scenesteward_app
APP_PASSWORD=${STAGING_APP_PW}
DATABASE_URL=postgresql+psycopg://scenesteward_app:${STAGING_APP_PW}@db:5432/scenesteward_staging
MIGRATION_DATABASE_URL=postgresql+psycopg://scenesteward_staging:${STAGING_OWNER_PW}@db:5432/scenesteward_staging
DATABASE_IDENTITY_SECRET=${STAGING_IDENTITY_SECRET}
REDIS_PASSWORD=${STAGING_REDIS_PW}
REDIS_URL=redis://:${STAGING_REDIS_PW}@redis:6379/0
APP_ENCRYPTION_KEY=${STAGING_FERNET_KEY}
APP_ENCRYPTION_CURRENT_KID=staging-primary-v1
STORAGE_PROVIDER=local
STORAGE_BUCKET=scenesteward-staging-documents
ANTIVIRUS_PROVIDER=clamav
CLAMAV_HOST=clamav
CLAMAV_PORT=3310
ANTIVIRUS_FAIL_CLOSED=true
AI_PROVIDER=offline
SWITCH_ADAPTER=test
FRONTEND_ORIGIN=http://localhost:3001
METRICS_ENABLED=true
EOF

chmod 600 backend/.env.staging
```

---

## 4. Key Rotation Procedures

### 4.1 Database Identity Secret Rotation
When rotating `DATABASE_IDENTITY_SECRET`:
1. Generate new 32-byte secret.
2. Run database migration script `scripts/rotate_identity_secret.py` connecting as schema owner.
3. The script writes the new secret to `private.app_secrets` within an atomic transaction.
4. Update `DATABASE_IDENTITY_SECRET` across all application instances.
5. Restart `api` and `worker` services.

### 4.2 Field-Level Encryption Key Rotation
When rotating `APP_ENCRYPTION_KEY`:
1. Generate new Fernet key.
2. Add new key to `APP_ENCRYPTION_KEYS` dictionary in environment with a new KID (e.g., `staging-2026-v2`).
3. Set `APP_ENCRYPTION_CURRENT_KID=staging-2026-v2`.
4. Run `scripts/reencrypt_pii.py` to re-encrypt existing ciphertext records without downtime.
5. Decommission old KID after verification.
