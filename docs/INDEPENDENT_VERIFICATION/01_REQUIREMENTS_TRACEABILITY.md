# SceneSteward — Independent Requirements Traceability Matrix

**Document ID:** `docs/INDEPENDENT_VERIFICATION/01_REQUIREMENTS_TRACEABILITY.md`  
**Auditor:** Independent Verification Team  
**Evaluation Standard:** Zero Trust — Verification by Reproducible Code & Test Execution  

---

## 1. Requirements Traceability Matrix

| Req ID | Requirement Description | Implementation Location | Database & Schema Dependencies | External Dependencies | Existing Tests | Independent Audit Verification | Findings & Observations | Status |
|:---:|:---|:---|:---|:---|:---|:---|:---|:---:|
| **REQ-01** | Multi-Tenant Data Isolation via RLS | `backend/app/core/database.py`, Alembic `c7a1e52b93f0` | 18 tables with `ENABLE ROW LEVEL SECURITY`, `scenesteward_app` role | PostgreSQL 18 | `test_tenant_isolation.py` (5 tests) | Executed adversarial connection injection test | Tenant boundary strictly isolates projects and participants at SQL level | **PASS** |
| **REQ-02** | HMAC-SHA256 Identity Trust Boundary | `fn_enforce_identity_trust()`, `compute_identity_sig()` | Trigger on `pg_catalog.set_config`, `users` table | None | `audit_adversarial_current.py` | Executed invalid signature, missing signature, and spoofing tests | Raw SQL parameter tampering fails with exception | **PASS** |
| **REQ-03** | 15 Canonical Consent Categories | `backend/app/core/choices.py:CONSENT_CATEGORIES` | `consent_choices.category` CHECK constraints | None | `test_consent_engine_matrix.py` (63 tests) | Executed boundary tests across all 15 categories | All 15 canonical categories present and evaluated in isolation | **PASS** |
| **REQ-04** | Non-Transitive Consent Invariant | `backend/app/services/consent_comparison.py` | `consent_choices`, `use_findings` | None | `test_consent_engine_matrix.py` | Executed cross-category inference attacks | Agreement to one category NEVER implies agreement to another | **PASS** |
| **REQ-05** | Silence is Never Agreement Invariant | `backend/app/services/consent_comparison.py` | `consent_choices` | None | `test_consent_engine_matrix.py` | Unaddressed categories test | Unanswered categories strictly evaluate to `not_discussed` or `needs_clarification` | **PASS** |
| **REQ-06** | Advisory AI Boundary | `backend/app/agents/`, `backend/app/api/v1/endpoints/reviews.py` | `reviews.review_status`, `reviews.rationale` | None | `test_complete_documentary_workflow.py` | Attempted AI auto-approval bypass | AI outputs remain advisory; human review requires written rationale | **PASS** |
| **REQ-07** | Document Intelligence & Adversarial Resistance | `backend/app/services/document_intelligence.py` | `document_pages`, `release_documents` | None | `test_document_intelligence.py` (6 tests) | Injected adversarial prompts (`[SYSTEM]`, `<<SYS>>`, zero-width chars) | Strips control characters, neutralizes injection, outputs advisory report | **PASS** |
| **REQ-08** | Antivirus & Malware Defense | `backend/app/services/malware_scanner.py` | `release_documents.storage_key` | ClamAV Daemon | `test_malware_scanner.py` | Tested fail-closed when ClamAV is offline in production | File uploads fail closed (HTTP 412/503) if scanner unreachable in prod | **PASS** |
| **REQ-09** | Cryptographic Participant Portal Tokens | `backend/app/core/security.py`, `backend/app/api/v1/endpoints/participants.py` | `participants.id`, `projects.id` | None | `test_tenant_isolation.py` | Tested token tampering, expired tokens, IDOR attacks | Tampered tokens rejected with HTTP 403; cross-project tokens denied | **PASS** |
| **REQ-10** | English / Hindi Bilingual Participant UX | `frontend/src/app/participant/[id]/page.tsx` | None | Next.js 14 | Next.js production build | Tested language switcher toggle in browser spec | All 15 categories and dignity guarantees localized in Hindi and English | **PASS** |
| **REQ-11** | Participant Withdrawal Flow | `backend/app/api/v1/endpoints/participants.py` | `tasks`, `audit_events` | Event Bus | `test_reporting_and_notifications.py` | Submitted withdrawal with `request_type="withdrawal"` | Immediately creates urgent task and logs audit event | **PASS** |
| **REQ-12** | Compliance Audit Export Package | `backend/app/api/v1/endpoints/projects.py` | `consent_records`, `consent_choices`, `audit_events` | None | `test_reporting_and_notifications.py` | Queried `GET /projects/{id}/audit-export` | Returns complete 15-category matrix and SHA256 integrity hash | **PASS** |
| **REQ-13** | Distributed Rate Limiting | `backend/app/core/rate_limiter.py` | None | Redis (with in-memory fallback) | `test_rate_limiter.py` | Tested Redis unavailable fallback and token burst | Gracefully falls back to local in-memory token bucket; protects endpoints | **PASS** |
| **REQ-14** | Fail-Closed Outbound Communication | `backend/app/services/communications.py` | `participant_communications` | Switch / Outbound provider | `test_complete_documentary_workflow.py` | Attempted unapproved dispatch and unconfigured provider | Returns HTTP 412 if unapproved, HTTP 503 if provider unconfigured | **PASS** |
| **REQ-15** | Disaster Recovery Verification | `backend/scripts/verify_isolated_restore.py` | PostgreSQL pg_dump / pg_restore | PostgreSQL 18 | Standalone runner | Executed against disposable PostgreSQL database | 0.29s RTO verified across 20 tables and 69 RLS policies | **PASS** |

---

## 2. Requirements Traceability Summary

- **Total Requirements Audited:** 15
- **PASS:** 15
- **FAIL:** 0
- **PARTIAL:** 0
- **BLOCKED:** 0
- **NOT TESTED:** 0
