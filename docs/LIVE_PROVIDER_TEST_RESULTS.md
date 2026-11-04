# SceneSteward — Live Provider Integration Test Results

**Date**: November 4, 2026  
**Auditor**: Principal Cloud Integration Engineer & QA Automation Specialist  
**Standard**: Honest Provider Verification Matrix (No Mock Reported as Live)  

---

## 1. Executive Summary

This document records the exact operational status of all external third-party integrations and database engines for SceneSteward. In accordance with zero-trust testing practices:
- Tests using in-memory mocks, offline fixtures, or loopback stubs are explicitly labeled as **`MOCK VERIFIED`** or **`LOCALLY TESTED`**.
- Only systems with verified live network transactions against production or staging hosts are designated **`LIVE_VERIFIED`**.
- Integrations awaiting API keys or cloud credentials in `.env` are recorded as **`CONFIGURED / BLOCKED LIVE`**.

---

## 2. Provider Integration Verification Ledger

| Provider / Subsystem | Integration Layer | Mode / Environment | Evidence & Test Results | Status |
|:---|:---|:---|:---|:---:|
| **PostgreSQL 18.6** | Primary Relational DB | Live Local Database (`127.0.0.1:5432`) | Real TCP queries, 4 migrations applied, RLS & triggers active, 107 tests passed | **`LIVE_VERIFIED`** |
| **Local File Storage** | File Storage Adapter | Live Local Filesystem (`var/storage`) | Full upload, download, sha256 checksum match, signed token validation | **`LIVE_VERIFIED`** |
| **Supabase Auth** | JWT JWKS Auth Verification | Offline RS256/ES256 Verification | Synthetic RSA keypair test passed (`test_supabase_jwks_offline_verification`); live staging JWKS endpoint unconfigured | **`CONFIGURED / BLOCKED LIVE`** |
| **Supabase Storage** | S3-Compatible Storage | HTTP Client Adapter | Signed URL generation & multipart adapter implemented; staging bucket URL/credentials unconfigured | **`CONFIGURED / BLOCKED LIVE`** |
| **Anthropic Claude** | AI Review Agents | Anthropic API Adapter | Offline synthetic evaluator passing (`test_offline_agents_produce_valid_outputs`); `ANTHROPIC_API_KEY` placeholder | **`CONFIGURED / BLOCKED LIVE`** |
| **Switch Collaboration**| Real-time Webhook & Outbox | Switch HTTP Client | Idempotent webhook receiver verified, payload HMAC verified, fail-closed outbox verified; live Switch endpoint unconfigured | **`CONFIGURED / BLOCKED LIVE`** |
| **ClamAV Antivirus** | Document Malware Scanner | TCP Daemon Adapter | EICAR mock test passing, fail-closed handling verified (`test_clamav_unavailable_fail_closed`); daemon not running | **`CONFIGURED / BLOCKED LIVE`** |

---

## 3. Detailed Provider Breakdown & Verification Criteria

### 3.1 PostgreSQL 18.6
- **Connection**: `postgresql+asyncpg://postgres:postgres@localhost:5432/scenesteward` (and `scenesteward_test`)
- **Runtime Role**: `scenesteward_app` with `NOBYPASSRLS`
- **Result**: `LIVE_VERIFIED`. All database queries, schema migrations (`0001_initial` through `e1f2a3b4c5d6`), RLS enforcement, and ACID transactions verified directly against PostgreSQL 18.6 engine.

### 3.2 Supabase Auth & JWT
- **Module**: `backend/app/core/security.py`
- **Current Behavior**:
  - Validates RS256 and ES256 signatures via PyJWT using JWKS cached keys.
  - Rejects unsigned, expired, wrong issuer, wrong audience, or tampered tokens.
  - In production (`APP_ENV=production`), `AUTH_PROVIDER=dev` is strictly forbidden and raises a startup validation error.
- **Blocker for Live Staging**: Requires active `SUPABASE_URL` and `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`.

### 3.3 Supabase S3-Compatible Storage
- **Module**: `backend/app/integrations/storage/supabase.py`
- **Current Behavior**: Implements secure pre-signed upload URL generation and HMAC token download verification with path-traversal prevention.
- **Blocker for Live Staging**: Requires active Supabase project with storage bucket `scenesteward-documents`.

### 3.4 Anthropic Claude AI Agents
- **Module**: `backend/app/agents/`
- **Current Behavior**:
  - Implements 5 specialized agents: `consent_analyst`, `story_change_analyst`, `participant_advocate`, `ethics_reviewer`, `production_coordinator`.
  - Enforces ethical prompt framing: input documents are treated strictly as untrusted data, never as prompt instructions.
  - Offline engine verifies structured JSON output schemas and flags prompt injection.
- **Blocker for Live Staging**: Requires valid `ANTHROPIC_API_KEY` with Claude 3.5 Sonnet quota.

### 3.5 Switch Webhook & Collaboration Adapter
- **Module**: `backend/app/integrations/switch/`
- **Current Behavior**:
  - Inbound webhook processing with HMAC-SHA256 signature verification.
  - Outbox retry pattern with exponential backoff and jitter (`backend/scripts/switch_retry.py`).
  - Strict rule: Inbound Switch events can NEVER modify participant consent records.
- **Blocker for Live Staging**: Requires reachable `SWITCH_BASE_URL` and webhook signing secret.

### 3.6 ClamAV Antivirus Daemon
- **Module**: `backend/app/services/malware_scanner.py`
- **Current Behavior**:
  - Scans uploaded byte streams against ClamAV over `INSTREAM` TCP protocol.
  - Detects EICAR test signatures and isolates infected files.
  - If `ANTIVIRUS_FAIL_CLOSED=true` and the daemon is unreachable, uploads are rejected with HTTP 503.
- **Blocker for Live Staging**: Requires running ClamAV container or host service on `CLAMAV_HOST:CLAMAV_PORT`.

