# SceneSteward — Current Implementation Audit & Traceability Matrix

**Date**: November 5, 2026  
**Auditor**: Principal Software Architect & QA Lead  
**Scope**: Full Repository Audit (FastAPI backend, PostgreSQL schema, RLS policies, integrations, testing harness)  
**Base Commit**: `5af4f02792835a2f1987be64958f43f1f153653a` (`main` / `develop`)  

---

## 1. Executive Implementation Status Overview

| Capability Area | Implementation State | Verification Status | Notes |
|:---|:---:|:---:|:---|
| **Core FastAPI Web Framework** | **100% Implemented** | **Pass (107 Tests)** | 48 REST endpoints, CORS, security headers, exception handling. |
| **PostgreSQL 18 Schema** | **100% Implemented** | **Pass (Catalog Audited)** | 20 tables, composite FKs, CHECK constraints, immutable audit triggers. |
| **Row-Level Security (RLS)** | **100% Implemented** | **Pass (Security Suite)** | 18 tables protected with 69 RLS policies and `NOBYPASSRLS`. |
| **HMAC-SHA256 Trust Boundary** | **100% Implemented** | **Pass (Security Suite)** | Context signing prevents spoofing of `app.current_user_id` or `app.is_system`. |
| **Consent Comparison Engine** | **100% Implemented** | **Pass (Unit Suite)** | Deterministic outcome evaluation (`ENGINE_VERSION = 1.0.0`). |
| **Document Processing & Virus Scan** | **100% Implemented** | **Pass (Container Wire)** | PDF/TXT extraction; fail-closed ClamAV socket (`zINSTREAM`). |
| **Advisory AI Agent Framework** | **100% Implemented** | **Pass (Offline & Unit)** | 5 agents; prompt-injection shielded; strictly advisory. |
| **Outbox Daemon & Retry Worker** | **100% Implemented** | **Pass (Worker Suite)** | Atomic lease sweeps, exponential backoff, dead-letter logging. |
| **Rate Limiting** | **Partial (In-Memory)** | **Preflight Only** | In-memory limiter in `main.py` needs distributed/Redis backend. |
| **Staging Docker Stack** | **100% Implemented** | **Pass (Container Wire)** | API, DB, ClamAV, and Worker running healthy in Docker. |
| **Frontend User Interface** | **0% Implemented** | **Pending Phase 5** | No frontend codebase exists yet; Next.js / TypeScript required. |
| **External Cloud Integrations** | **Adapters Ready** | **Mock / Staging Verified** | Supabase Auth/Storage and Switch ready for live cloud credentials. |

---

## 2. Implemented vs. Mocked vs. Unverified Integrations

| Integration Partner | Adapter Module | Offline / Mock State | Live Connection State | Action Required |
|:---|:---|:---:|:---:|:---|
| **PostgreSQL 18** | `app.core.database` | Tested via test DB | **LIVE VERIFIED** (Container port 5433) | Operational in local container. |
| **ClamAV Antivirus** | `app.services.malware_scanner` | Mock socket tested | **LIVE VERIFIED** (Container port 3310) | Clean + EICAR intercepted live. |
| **Outbox Worker** | `scripts.switch_retry` | Simulated retries | **LIVE VERIFIED** (Worker container daemon) | Continuously sweeping in Docker. |
| **Supabase Auth** | `app.integrations.auth.supabase` | Tested via local JWKS | **UNVERIFIED (Cloud)** | Requires live Supabase project credentials. |
| **Supabase Storage** | `app.integrations.storage.signed` | Local filesystem fallback | **UNVERIFIED (Cloud)** | Requires live private S3/Supabase bucket. |
| **Anthropic Claude** | `app.agents.base` | Deterministic offline default | **UNVERIFIED (Cloud)** | Requires live Anthropic API key. |
| **Switch Network** | `app.integrations.switch.adapter` | In-memory event sink | **UNVERIFIED (Cloud)** | Requires live Switch server URL and key. |

---

## 3. Identified Gaps, Weaknesses & Technical Risks

1. **Rate Limiting**: `app.main.py` uses an in-memory dictionary (`_rate_limits: dict[str, list[float]]`) with naive cleanup. In multi-worker deployments (e.g. Uvicorn with multiple workers or Kubernetes pods), rate counters are not shared, and spoofed `X-Forwarded-For` headers could bypass limits without proxy validation.
2. **Startup Secret Validation**: While `_production_guard` blocks `APP_ENV=production` when using `dev` auth or encryption defaults, staging and production startup must strictly fail if critical credentials (`DATABASE_IDENTITY_SECRET`, `APP_ENCRYPTION_KEY`) match known defaults or placeholders.
3. **Frontend Absence**: The backend is fully developed with 48 endpoints, but no frontend interface exists. Production staff and documentary participants currently have no UI to manage projects, upload documents, or review consent choices.
4. **Browser E2E Automation**: Test coverage is strong across backend unit, integration, and security layers (107 tests), but lacks automated browser/UI tests (e.g. Playwright) driving real user journeys.
5. **Continuous Integration**: The repository lacks GitHub Actions workflow files to automatically enforce Ruff, Pytest, migration checks, and container builds on pull requests.

---

## 4. Feature-to-Code-to-Test Traceability Matrix

| Feature / Domain Responsibility | Primary Code Modules | Database Tables / Migrations | Automated Test Files |
|:---|:---|:---|:---|
| **Identity & Authentication** | `app.api.v1.endpoints.auth`<br>`app.core.security`<br>`app.integrations.auth` | `users`<br>`c7a1e52b93f0_least_privilege_and_rls` | `tests/integration/test_auth.py` (12 tests) |
| **Project & Team RBAC** | `app.api.v1.endpoints.projects`<br>`app.api.dependencies` | `projects`<br>`project_memberships` | `tests/security/test_rbac.py` (10 tests) |
| **Participant PII & Fernet Cryptography** | `app.api.v1.endpoints.participants`<br>`app.services.encryption` | `participants`<br>`participant_contact_records` | `tests/unit/test_encryption.py` (7 tests) |
| **Scoped Consent & Versioning** | `app.api.v1.endpoints.consent`<br>`app.services.consent_service` | `consent_records`<br>`consent_choices` | `tests/integration/test_failure_modes.py` |
| **Deterministic Scope Comparison** | `app.services.consent_comparison`<br>`app.workflows.proposed_use_analysis` | `proposed_uses`<br>`proposed_use_analyses` | `tests/unit/test_comparison_engine.py` (10 tests) |
| **Advisory AI Agent Pipeline** | `app.agents.*`<br>`app.services.agent_context` | `agent_runs`<br>`agent_run_evaluations` | `tests/agents/test_agents.py` (11 tests) |
| **Document Storage & ClamAV** | `app.api.v1.endpoints.documents`<br>`app.services.malware_scanner` | `release_documents`<br>`release_document_pages` | `tests/integration/test_documents.py` (12 tests) |
| **Document Text Extraction** | `app.workflows.document_extraction` | `release_document_pages` | `tests/integration/test_extraction.py` (5 tests) |
| **Human Review & Care Tasks** | `app.api.v1.endpoints.reviews`<br>`app.services.tasks` | `reviews`<br>`tasks` | `tests/e2e/test_beyond_the_silence.py` (2 tests) |
| **Communications & Audit Logging** | `app.api.v1.endpoints.communications`<br>`app.services.audit` | `participant_communications`<br>`audit_events` | `tests/integration/test_communications.py` (2 tests) |
| **Switch Integration & Outbox** | `app.integrations.switch.*`<br>`scripts/switch_retry.py` | `integration_events`<br>`switch_room_links` | `tests/integration/test_switch.py` (8 tests) |
| **PostgreSQL RLS & HMAC Boundary** | `app.core.database`<br>`backend/migrations/versions/*` | All 18 RLS tables<br>`e1f2a3b4c5d6` | `tests/security/test_rls_isolation.py` (8 tests)<br>`tests/security/test_trust_boundary.py` (7 tests) |
| **Operational Metrics** | `app.api.v1.endpoints.metrics`<br>`app.services.metrics` | System telemetry | `tests/integration/test_metrics.py` (2 tests) |
| **Full Production Lifecycle** | `app.workflows.*` | Entire schema | `tests/e2e/test_integrated_lifecycle.py` (1 test) |

**Total Verified Tests**: 107 passed across 13 test files.
