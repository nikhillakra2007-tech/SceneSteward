# SceneSteward — Staging Configuration & Security Audit

**Date**: November 4, 2026  
**Auditor**: Application Security Engineer & PostgreSQL Security Auditor  
**Scope**: Environment Variables, Configuration Loaders, Security Gates, Leakage Prevention  

---

## 1. Environment Variables Audit (`backend/.env.staging.example`)

Every setting required for staging operations is explicitly declared with safe placeholder values:

| Environment Variable | Declared in Template | Required / Optional | Purpose & Fail-Closed Guard |
|:---|:---:|:---:|:---|
| `APP_ENV` | YES | Required | Set to `staging`. Activates strict production/staging guards. |
| `DATABASE_URL` | YES | Required | PostgreSQL connection string for unprivileged runtime role `scenesteward_app` (`NOBYPASSRLS`). |
| `MIGRATION_DATABASE_URL` | YES | Required | PostgreSQL connection string for schema owner `scenesteward` (used ONLY by Alembic). |
| `DATABASE_IDENTITY_SECRET` | YES | Required | High-entropy HMAC secret used by application and PostgreSQL `SECURITY DEFINER` functions for RLS claims. |
| `AUTH_PROVIDER` | YES | Required | Set to `supabase`. Rejects dev tokens immediately if `app_env=staging`. |
| `SUPABASE_URL` | YES | Required | Base URL of staging Supabase project. |
| `SUPABASE_ANON_KEY` | YES | Required | Staging Supabase anon client key. |
| `SUPABASE_SERVICE_ROLE_KEY` | YES | Required | Staging Supabase service-role key (server-side only, used for private bucket management). |
| `AUTH_JWKS_URL` | YES | Required | JWKS endpoint (`/auth/v1/.well-known/jwks.json`) for RS256/ES256 signature verification. |
| `AUTH_ISSUER` | YES | Required | Expected JWT issuer claim (`SUPABASE_URL/auth/v1`). |
| `AUTH_AUDIENCE` | YES | Required | Expected JWT audience claim (`authenticated`). |
| `STORAGE_PROVIDER` | YES | Required | Set to `supabase`. Rejects insecure fallback storage. |
| `STORAGE_BUCKET` | YES | Required | Private bucket name (`scenesteward-staging-documents`). |
| `APP_ENCRYPTION_KEY` | YES | Required | 256-bit Fernet key for encrypting participant PII (legal names, phones, emails). |
| `APP_ENCRYPTION_CURRENT_KID`| YES | Required | Key ID supporting zero-downtime key rotation (`staging-primary-2026-v1`). |
| `ANTIVIRUS_PROVIDER` | YES | Required | Set to `clamav`. |
| `CLAMAV_HOST` | YES | Required | ClamAV daemon hostname (`clamav` in Docker, `127.0.0.1` native). |
| `CLAMAV_PORT` | YES | Required | ClamAV TCP port (default 3310). |
| `ANTIVIRUS_FAIL_CLOSED` | YES | Required | Set to `true`. Rejects uploads with HTTP 503 if scanner is offline. |
| `AI_PROVIDER` | YES | Required | Set to `anthropic`. |
| `ANTHROPIC_API_KEY` | YES | Required | Staging Anthropic Claude API key. |
| `AI_MODEL` | YES | Required | Set to `claude-sonnet-4-5`. |
| `SWITCH_ADAPTER` | YES | Required | Set to `http`. |
| `SWITCH_BASE_URL` | YES | Required | Base URL for staging Switch collaboration instance. |
| `SWITCH_API_KEY` | YES | Required | Agent API authentication key. |
| `SWITCH_AGENT_ID` | YES | Required | Agent identifier registered on Switch platform. |

---

## 2. Configuration Loader Verification

The configuration loader (`backend/app/core/config.py`) was verified to support flexible staging redirection:
```python
@lru_cache
def get_settings() -> Settings:
    env_file = os.environ.get("SCENESTEWARD_ENV_FILE") or os.environ.get("ENV_FILE")
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()
```

### Dynamic Loading Verification Test
Executed in Python:
```python
os.environ['ENV_FILE'] = 'backend/.env.staging.example'
s = get_settings()
assert s.app_env == 'staging'
assert s.app_name == 'SceneSteward-Staging'
```
**Result**: **PASS**. The application reliably targets the staging configuration without modifying `.env`.

---

## 3. Dev Provider Lockout Audit

A critical security invariant is that development mock providers (such as dev HS256 tokens or local storage) must never silently activate in a staging or production environment.

### Enforcement in `backend/app/core/config.py`:
```python
@model_validator(mode="after")
def _production_guard(self) -> Settings:
    if (self.is_production or self.is_staging) and self.auth_provider == "dev":
        raise ValueError(f"AUTH_PROVIDER=dev is not permitted in APP_ENV={self.app_env}; configure Supabase or another real IdP")
    if (self.is_production or self.is_staging) and not self.app_encryption_key:
        raise ValueError(f"APP_ENCRYPTION_KEY must be set in APP_ENV={self.app_env}")
    return self
```

### Adversarial Verification Test
Attempted instantiation:
```python
Settings(app_env='staging', auth_provider='dev', database_url='...', app_encryption_key='...')
```
**Outcome**: Instantiation threw `1 validation error for Settings: Value error, AUTH_PROVIDER=dev is not permitted in APP_ENV=staging`.  
**Result**: **PASS**. Development auth cannot silently activate in staging.

---

## 4. Secret Exposure & Logging Audit

An audit of application logging, startup checks, and error responses confirmed:
1. **Startup Checks**: `startup_checks(s)` reports configuration status by variable name only (`{'check': 'DATABASE_URL', 'status': 'configured'}`). Zero secrets are printed.
2. **Health Endpoints**: `GET /health` outputs service status (`healthy`/`unhealthy`) without environmental dumps.
3. **HTTP 500 Responses**: Unhandled exceptions are scrubbed; stack traces are logged internally and clients receive standardized error envelopes with correlation IDs.
4. **Git Exposure**: `.gitignore` contains `.env` and `.env.*`. `git check-ignore` confirms `backend/.env.staging` is uncommitted.

