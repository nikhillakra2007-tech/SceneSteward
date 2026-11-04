# SceneSteward — Live Integration Verification Report

**Date**: November 4, 2026  
**Audience**: Principal Architects, SREs, Product Security, and Cloud Engineers  
**Core Policy**: *Never fake live external integrations. Distinguish local/offline verification from live service verification.*

---

## 1. Project Maturity Milestones

SceneSteward development is tracked across three distinct progression gates:

1. **Milestone 1 — Staging Candidate (`VERIFIED & COMPLETED`)**:
   - Authoritative PostgreSQL 18.6 relational database operating with 21 tables.
   - Database identity trust boundary enforced via HMAC-SHA256 signatures (`e1f2a3b4c5d6`).
   - 18 project-scoped tables protected by 69 Row Level Security policies.
   - Composite foreign keys preventing cross-project linkage.
   - Immutability triggers protecting confirmed consent records and audit ledgers.
   - Full 48 REST API endpoints verified under FastAPI.
   - 107 automated unit, integration, security, and e2e lifecycle tests passing with 100% pass rate.
   - Disaster recovery sub-second restore verified (0.58s RTO).
2. **Milestone 2 — Live Staging (`READY FOR CREDENTIAL PROVISIONING`)**:
   - Real staging Supabase Auth JWKS token verification.
   - Real staging Supabase Storage private bucket upload/download.
   - Live Anthropic Claude 3.5 Sonnet Messages API key connection.
   - Live Switch Core hub connection via SSE and HTTP agent protocol.
   - Live ClamAV daemon running on staging network.
3. **Milestone 3 — Production Candidate (`DOCUMENTED & GATED`)**:
   - Production container deployment, read-only root filesystems, automated health probes, independent penetration review, and multi-region disaster recovery runbooks.

---

## 2. External Provider Status & Verification Ledger

| Provider | Protocol / Interface | Integration Status | Verification Evidence | Exact Required Configuration for Live Activation |
|---|---|---|---|---|
| **PostgreSQL 18.6** | TCP / `psycopg3` | **`LIVE_VERIFIED`** | All 107 regression tests passing against PostgreSQL 18.6. Direct-SQL RLS tests executed under `scenesteward_app` (`NOBYPASSRLS`). Sub-second isolated disaster recovery (0.58s RTO). | `DATABASE_URL`, `DATABASE_URL_ADMIN`, `MIGRATION_DATABASE_URL` (Active). |
| **Prometheus / Metrics** | HTTP `/api/v1/metrics` | **`LIVE_VERIFIED`** | Endpoint verified returning in-memory request counters, latency percentiles, and database connection pool gauges in JSON and Prometheus formats. | `METRICS_ENABLED=true` (Active). |
| **Local Private Storage** | Local FS + HMAC URLs | **`LIVE_VERIFIED`** | End-to-end file upload, PUT via signed URL, magic-byte sniffing, decompression bomb defense, and authorized GET roundtrip passing in `test_documents.py`. | `STORAGE_PROVIDER=local` (Active for dev/tests). |
| **Supabase Auth** | RS256 / ES256 JWKS | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | Full PyJWKClient token decoder implemented in `app/core/security.py`. Validated via synthetic RSA256 keypairs in `test_auth.py`. Dev provider prohibited in production. | In `.env`: Set `AUTH_PROVIDER=supabase`, `SUPABASE_URL=https://<project>.supabase.co`, `AUTH_JWKS_URL=https://<project>.supabase.co/auth/v1/.well-known/jwks.json`, and `SUPABASE_ANON_KEY`. |
| **Supabase Storage** | REST / S3 Multipart | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | Private bucket adapter implemented in `app/integrations/storage/supabase.py` with signed upload targets and download URLs. | In `.env`: Set `STORAGE_PROVIDER=supabase`, `STORAGE_BUCKET=scenesteward-private`, `SUPABASE_SERVICE_ROLE_KEY`. |
| **Anthropic Claude 3.5** | HTTPS / Messages API | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | Client implemented in `app/integrations/ai/anthropic_provider.py`. Deterministic rule-based heuristic fallback tested across 5 specialist agents in `test_agents.py`. | In `.env`: Set `AI_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=sk-ant-api03-...`, `AI_MODEL=claude-sonnet-4-5`. |
| **Switch Collaboration Hub** | SSE / HTTP Agent Protocol | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | Adapter implemented in `app/integrations/switch/http_adapter.py`. Transactional outbox sweeper (`switch_retry.py`) with `SKIP LOCKED` tested across 8 tests in `test_switch.py`. | In `.env`: Set `SWITCH_ADAPTER=http`, `SWITCH_BASE_URL=http://<host>:8000`, `SWITCH_API_KEY`, `SWITCH_AGENT_ID`. |
| **ClamAV Antivirus** | ClamD TCP (`zINSTREAM`) | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | TCP client implemented in `app/services/malware_scanner.py`. EICAR signature detection and fail-closed security mode verified in `test_failure_modes.py`. | In `.env`: Set `ANTIVIRUS_PROVIDER=clamav`, `CLAMAV_HOST=127.0.0.1`, `CLAMAV_PORT=3310`, `ANTIVIRUS_FAIL_CLOSED=true`. |
| **Docker OCI Container** | Multi-Stage Linux OCI | **`CONFIGURED_BUT_UNVERIFIED`** | Production Dockerfile created with non-root user (UID 10001), healthcheck, and docker-compose deployment manifests. | Execute `docker compose up --build` on Linux staging host with Docker engine. |

---

## 3. Degradation & Fail-Closed Protocols

1. **Malware Scanner Outage**:
   - If `ANTIVIRUS_FAIL_CLOSED=true` (mandatory for production/staging), any connection failure or timeout to ClamAV rejects document uploads immediately with HTTP 412/503 (`malware_scanner_unavailable`).
2. **AI Provider Outage**:
   - If Anthropic Claude times out or is rate-limited (429), the workflow falls back to offline heuristic analysis. The system records an audit event and flags the proposed use for human review (`NEEDS_DISCUSSION`). It never halts production or claims false success.
3. **Switch Hub Outage**:
   - Outbox events remain in `failed` state with exponential retry caps. User workflows are never interrupted. After 3 attempts, unrecoverable events are escalated to `dead_letter` and notify human care leads.

