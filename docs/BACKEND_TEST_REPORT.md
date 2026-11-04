# SceneSteward Backend Test Execution Report

**Date**: November 4, 2026  
**Platform**: Python 3.12.10, pytest 9.2.0, PostgreSQL 18.6  
**Test Framework**: `pytest`, `pytest-anyio`, `httpx`, `FastAPI TestClient`  
**Total Test Cases**: 107  
**Passing**: 107 (100%)  
**Failing**: 0 (0%)  
**Execution Duration**: 50.56 seconds  
**Static Analysis**: `ruff check .` — All checks passed (0 errors)

---

## 1. Test Distribution by Category

| Category | Suite File | Count | Pass Rate | Execution Time | Description |
|---|---|---:|:---:|:---:|---|
| **E2E Acceptance** | `test_beyond_the_silence.py` | 2 | 100% | 2.1s | Canonical acceptance scenario for participant consent protection |
| **E2E Lifecycle** | `test_integrated_lifecycle.py` | 1 | 100% | 1.9s | 24-step end-to-end documentary production lifecycle verification |
| **Agent Intelligence**| `test_agents.py` | 11 | 100% | 2.4s | 5 advisory agents, error handling, prompt immutability |
| **Auth & Revocation**| `test_auth.py` | 12 | 100% | 2.6s | JWT validation, RS256 JWKS mock, immediate revocation |
| **Communications** | `test_communications.py` | 2 | 100% | 0.9s | Human approval required, fail-closed 503 delivery |
| **Document Pipeline**| `test_documents.py` | 12 | 100% | 3.5s | Signed URLs, sniff validation, EICAR malware, bomb guard |
| **Text Extraction** | `test_extraction.py` | 5 | 100% | 2.2s | Plain-text / PDF extraction, unconfirmed consent proposals |
| **Failure & Recovery**| `test_failure_modes.py` | 6 | 100% | 6.1s | AI timeout/rate-limiting, ClamAV fail-closed, optimistic concurrency, storage failures |
| **Observability** | `test_metrics.py` | 2 | 100% | 0.4s | JSON and Prometheus exposition formats |
| **Migrations** | `test_migrations.py` | 4 | 100% | 3.8s | Schema drift, upgrade, downgrade, re-upgrade cycle (`e1f2a3b4c5d6`) |
| **Switch Integration**| `test_switch.py` | 8 | 100% | 2.3s | Transactional outbox, atomic `SKIP LOCKED` batch sweep |
| **RBAC Security** | `test_rbac.py` | 10 | 100% | 5.1s | 6 project roles, cross-project isolation, demotion guards |
| **RLS Isolation** | `test_rls_isolation.py` | 8 | 100% | 3.2s | Direct-SQL RLS policy evaluation under `scenesteward_app` |
| **Trust Boundary & FKs**| `test_trust_boundary.py` | 7 | 100% | 1.5s | HMAC SHA-256 signature gating, secret isolation, composite FKs, concurrency, rollback, privilege escalation |
| **Comparison Engine** | `test_comparison_engine.py` | 10 | 100% | 0.6s | Deterministic 15-category matrix comparison |
| **Key Ring Encryption**| `test_encryption.py` | 7 | 100% | 1.2s | Versioned key ring, legacy fallback, key rotation |
| **Total** | | **107** | **100%** | **50.56s** | |

---

## 2. Key Scenarios Verified

1. **The 24-Step Integrated Lifecycle**:
   - Authenticated user identities -> project creation -> membership assignment -> participant creation -> encrypted contact storage -> proposed use draft -> version update -> signed upload URL -> PUT bytes -> complete upload -> document text extraction -> AI agent analysis -> database persistence -> comparison outcome (`NEEDS_DISCUSSION`) -> pending human review -> explicit human decision -> updated confirmed consent -> immutable history -> draft communication -> care lead approval -> fail-closed delivery check (503) -> append-only audit verification -> Switch outbox batch sweep -> final project state retrieval.
2. **Beyond the Silence Acceptance Scenario**:
   - Amara Okoro verbal consent for interview recording cannot be stretched to cover promotional trailers or AI voice synthesis; outcome remains strictly `NEEDS_DISCUSSION`.
3. **Cryptographic Database Trust Boundary (Alembic `e1f2a3b4c5d6`)**:
   - `scenesteward_app` cannot spoof `app.user_id` without a valid HMAC signature.
   - `scenesteward_app` cannot bypass RLS via `app.system='on'` without a valid HMAC signature.
   - `scenesteward_app` cannot read `private.app_secrets`.
   - Cross-project entity linkage is rejected at the database level by composite foreign keys (`(participant_id, project_id)`).
   - Privilege escalation (`SET ROLE`, `CREATE TABLE`, `TRUNCATE`) denied with `InsufficientPrivilege`.
4. **Failure Modes & Recovery**:
   - Anthropic timeout and 429 rate-limiting fail closed safely without corrupting analysis states.
   - ClamAV scanner unavailable rejects documents when `ANTIVIRUS_FAIL_CLOSED=true`.
   - Concurrent consent confirmation rejects stale version submissions without corrupting the confirmed record.
   - Partial storage failures discard database records and clean up orphaned files.
