# SceneSteward External Integration Status Report

**Date**: November 4, 2026  
**Integration Classification Rule**: *Never fake live external integrations. Distinguish local/offline verification from live cloud verification.*

---

## 1. Classification Status Tiers

- **`LIVE_VERIFIED`**: Tested and running against an actual, active service instance with live protocol verification and bidirectional communication.
- **`OFFLINE_VERIFIED`**: Full protocol adapter, payload serialization, error handling, and behavioral logic verified against deterministic offline doubles or mock engines in the test harness.
- **`CONFIGURED_BUT_UNVERIFIED`**: Production adapter code complete and configuration schema validated; awaiting live staging credentials/endpoints.
- **`BLOCKED`**: Missing implementation or failing dependency.

---

## 2. Integration Status Matrix

| Integration Target | Protocol / Mode | Classification | Evidence & Test Coverage | Operational Staging Promotion Requirements |
|---|---|---|---|---|
| **PostgreSQL 18.6** | Native TCP / `psycopg3` | **`LIVE_VERIFIED`** | Live database connected on port 5432. All 98 regression tests passed. Live RLS policy enforcement, 180 catalog triggers, HMAC trust boundary (`e1f2a3b4c5d6`), and adversarial penetration tests verified. | Production configuration requires dedicated DB connection pooling (e.g. PgBouncer) and read-replica routing. |
| **Prometheus Metrics** | HTTP `/api/v1/metrics` | **`LIVE_VERIFIED`** | Live `/api/v1/metrics` endpoint reporting request counts, HTTP duration histograms, database connection pool statistics, and outbox queue backlog. | Scrape job configuration in Prometheus/Grafana server. |
| **Supabase Auth** | RS256 / ES256 JWKS | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | JWT decoding, claims verification, role mapping, and JIT provisioning verified via `mint_dev_token` and offline RS256 token verification in `test_auth.py`. | Provide `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_JWT_SECRET` in staging `.env`. |
| **Supabase Storage** | REST / S3 Multipart | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | `LocalStorageProvider` with HMAC signed URLs 100% verified in end-to-end upload/download lifecycle. Cloud adapter implemented with signed upload/download tokens. | Provide `SUPABASE_STORAGE_BUCKET` and credentials in staging `.env`. |
| **Anthropic Claude 3.5** | HTTPS / REST Claude API | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | Offline heuristic AI provider verified across all 5 agent tests (`test_consent_auditor.py`, `test_boundary_detective.py`, `test_fair_use.py`, etc.). Fallback logic and JSON extraction verified. | Provide valid `ANTHROPIC_API_KEY` in staging `.env`. |
| **Switch Collaboration Hub** | SSE / HTTP Agent Protocol | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | Outbox pattern with atomic `SELECT ... FOR UPDATE SKIP LOCKED` sweeper (`switch_retry.py`) and mock Switch adapter passing all tests. | Deploy Switch Core service and configure `SWITCH_BASE_URL` and `SWITCH_API_KEY`. |
| **ClamAV Anti-Virus** | ClamD TCP Stream | **`OFFLINE_VERIFIED`** / `CONFIGURED_BUT_UNVERIFIED` | EICAR signature byte detection, decompression bomb guards, and fail-closed security mode verified in `test_documents.py`. | Run ClamAV daemon container (`clamav/clamav:latest`) listening on port 3310. |
| **Docker / Containerization** | Linux OCI Container | **`CONFIGURED_BUT_UNVERIFIED`** | Multi-stage Dockerfile and docker-compose configurations defined. Non-root user execution, read-only root filesystem specified. | Execute automated staging container build and smoke-test on Linux CI/CD runner. |

---

## 3. Fail-Closed & Degraded Operation Controls

1. **Anti-Virus Outage**:
   - When `ANTIVIRUS_FAIL_CLOSED=true`, document uploads are rejected if ClamAV daemon is unreachable.
   - When set to `false`, files are tagged `unscanned` and flagged for quarantined asynchronous review.
2. **AI Provider Outage**:
   - If Anthropic API responds with rate-limit (429) or downtime (5xx), the pipeline automatically degrades to rule-based fallback without halting the review workflow.
3. **Switch Hub Outage**:
   - Outbox events persist in PostgreSQL with exponential backoff retry. No user-facing documentary workflow is interrupted.
