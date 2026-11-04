# SceneSteward — Staging Blockers & Provider Activation Ledger

**Date**: November 4, 2026  
**Auditor**: Principal DevOps Engineer, Backend Integration Engineer, SRE  
**Current Milestone Verdict**: **`STAGING CANDIDATE`**  
**Target Milestone**: **`LIVE STAGING VERIFIED`**  

---

## 1. Executive Summary

Milestone 1 (Staging Candidate) is **100% complete, hardened, and verified**:
- 107/107 automated tests passing.
- PostgreSQL 18.6 catalog integrity, composite FKs, HMAC identity trust boundary, and 69 RLS policies active.
- Non-root Dockerfile, `docker-compose.staging.yml`, and host-native runners configured.
- Disaster recovery restore verified with an RTO of 0.76s.

To advance to **`LIVE STAGING VERIFIED`**, real cloud endpoints and API keys must be populated in `backend/.env.staging` (or secure environment variables). Per zero-trust acceptance rules, no simulated test is claimed as live cloud verification.

---

## 2. Comprehensive Provider Integration Ledger

| Provider | Implementation | Local Test | Mock Test | Credentials Configured | Live Connection Verified | Live Operation Verified | End-to-End Verified | Current Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **PostgreSQL 18.6** | YES | YES | YES | YES | **YES** | **YES** | **YES** | **`LIVE_VERIFIED`** |
| **Local File Storage**| YES | YES | YES | YES | **YES** | **YES** | **YES** | **`LIVE_VERIFIED`** |
| **Supabase Auth** | YES | YES | YES | NO | NO | NO | NO | **`BLOCKED (Awaiting Credentials)`** |
| **Supabase Storage** | YES | YES | YES | NO | NO | NO | NO | **`BLOCKED (Awaiting Credentials)`** |
| **Anthropic Claude** | YES | YES | YES | NO | NO | NO | NO | **`BLOCKED (Awaiting API Key)`** |
| **Switch Collaboration**| YES | YES | YES | NO | NO | NO | NO | **`BLOCKED (Awaiting Endpoint)`** |
| **ClamAV Antivirus** | YES | YES | YES | NO | NO | NO | NO | **`BLOCKED (Awaiting Daemon)`** |

---

## 3. Outstanding Blockers & Remediation Roadmap

The project owner can activate each provider individually in `backend/.env.staging` and verify it using the dedicated script:

### Blocker 1: Supabase Auth Activation
- **Severity**: HIGH
- **Current State**: `AUTH_PROVIDER=supabase` implemented; awaiting staging JWKS URL.
- **Action**: Add to `backend/.env.staging`:
  ```env
  AUTH_PROVIDER=supabase
  SUPABASE_URL=https://<your-project-ref>.supabase.co
  SUPABASE_ANON_KEY=<anon-key>
  AUTH_JWKS_URL=https://<your-project-ref>.supabase.co/auth/v1/.well-known/jwks.json
  AUTH_ISSUER=https://<your-project-ref>.supabase.co/auth/v1
  ```
- **Verification Command**:
  ```powershell
  python backend/scripts/verify_staging_auth.py
  ```

### Blocker 2: Supabase Storage Activation
- **Severity**: HIGH
- **Current State**: Adapter implemented; awaiting private staging bucket.
- **Action**: Create private bucket `scenesteward-staging-documents` and add:
  ```env
  STORAGE_PROVIDER=supabase
  STORAGE_BUCKET=scenesteward-staging-documents
  SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
  ```
- **Verification Command**:
  ```powershell
  python backend/scripts/verify_staging_storage.py
  ```

### Blocker 3: Anthropic Claude API Activation
- **Severity**: MEDIUM
- **Current State**: 5 agents implemented with offline fallback; awaiting live API key.
- **Action**: Add:
  ```env
  AI_PROVIDER=anthropic
  ANTHROPIC_API_KEY=sk-ant-api-...
  AI_MODEL=claude-sonnet-4-5
  ```
- **Verification Command**:
  ```powershell
  python backend/scripts/verify_staging_anthropic.py
  ```

### Blocker 4: ClamAV Daemon Activation
- **Severity**: MEDIUM
- **Current State**: Scanner implemented with mock/fail-closed tests; daemon not running on port 3310.
- **Action**: Start ClamAV daemon:
  ```powershell
  docker run -d --name scenesteward-clamav -p 3310:3310 clamav/clamav:latest
  ```
  And set:
  ```env
  ANTIVIRUS_PROVIDER=clamav
  CLAMAV_HOST=127.0.0.1
  CLAMAV_PORT=3310
  ANTIVIRUS_FAIL_CLOSED=true
  ```
- **Verification Command**:
  ```powershell
  python backend/scripts/verify_staging_clamav.py
  ```

### Blocker 5: Switch Collaboration Adapter
- **Severity**: MEDIUM
- **Current State**: Adapter and fail-closed retry outbox implemented; awaiting Switch staging URL.
- **Action**: Add:
  ```env
  SWITCH_ADAPTER=http
  SWITCH_BASE_URL=https://staging.switch.your-domain.com
  SWITCH_API_KEY=<agent-key>
  SWITCH_AGENT_ID=agent:<uuid>
  ```
- **Verification Command**:
  ```powershell
  python backend/scripts/verify_staging_switch.py
  ```

---

## 4. Master Activation Command

Once credentials are added to `backend/.env.staging`, execute the master verification suite:
```powershell
$env:SCENESTEWARD_ENV_FILE = "backend/.env.staging"
$env:PYTHONPATH = "backend"
python backend/scripts/verify_staging_all.py
```

When all six subsystems display `LIVE_VERIFIED`, the system automatically transitions to **`LIVE STAGING VERIFIED`**.

