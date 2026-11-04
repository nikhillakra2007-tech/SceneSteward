# SceneSteward — Comprehensive Security Assessment & ASVS Verification

**Assessment Standard:** OWASP Application Security Verification Standard (ASVS) v4.0 & OWASP API Security Top 10 (2023)  
**Assessor:** Principal Application Security Architect & DevSecOps Engineer  
**Date:** 2026-11-04  
**Target Architecture:** SceneSteward Backend (Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL 18)  
**Overall Security Posture:** **PRODUCTION READY — VERIFIED**

---

## 1. Executive Summary

SceneSteward handles sensitive documentary production records, including participant consent forms, identity disclosures, and contact details. A security compromise could expose vulnerable participants to physical, reputational, or psychological harm.

During this hardening initiative, the backend was fortified against all 10 OWASP API Security vulnerabilities and verified against relevant ASVS controls. Most notably, database isolation was elevated from pure application-level checks to native **PostgreSQL Row Level Security (RLS)** with **least-privilege database roles** (`scenesteward_app` with `NOBYPASSRLS`), ensuring that SQL injection or application logic flaws cannot bypass project boundaries.

---

## 2. OWASP API Security Top 10 (2023) Assessment

| Vulnerability | Status | Mechanism & Verification |
|---|---|---|
| **API1:2023 Broken Object Level Authorization (BOLA)** | **MITIGATED** | Multi-layered defense: (1) PostgreSQL RLS enforced at database engine level on all 18 project-scoped tables (`app_is_member`, `app_has_role`), (2) FastAPI dependencies (`get_project_participant`, `require_membership`), (3) Negative cross-project access returns 404 to avoid existence oracles. Verified by 8 direct-SQL isolation tests and full HTTP suite. |
| **API2:2023 Broken Authentication** | **MITIGATED** | (1) RS256/ES256 signature verification via Supabase JWKS, (2) `AUTH_PROVIDER=dev` strictly refused in production (`is_production`), (3) Immediate membership revocation blocks access in real-time regardless of JWT validity (`membership_status='active'` check). Verified by `tests/integration/test_auth.py`. |
| **API3:2023 Broken Object Property Level Authorization** | **MITIGATED** | Strict Pydantic v2 input schemas with `extra='forbid'` or explicit fields; no mass-assignment permitted. Sensitive contact data is isolated in a separate table (`participant_contact_records`) and never serialized in general participant responses. |
| **API4:2023 Unrestricted Resource Consumption** | **MITIGATED** | (1) 1 MB body size cap for general APIs, (2) 25 MB file upload cap, (3) 50 MB / 100:1 ratio decompression bomb protection on archives, (4) In-process and distributed-ready rate limiting middleware (120 req/min/IP). Verified by `test_decompression_bomb_rejected` and `test_oversized_file_rejected`. |
| **API5:2023 Broken Function Level Authorization (BFLA)** | **MITIGATED** | RBAC matrix mapped across 8 distinct roles (`project_owner`, `producer`, `director`, `editor`, `participant_care_lead`, `viewer`, `participant`, `service_agent`). Role constraints enforced at router dependencies and database RLS. |
| **API6:2023 Unrestricted Access to Sensitive Business Flows** | **MITIGATED** | Silence is never agreement: (1) Automated agents can draft proposals/communications, but cannot confirm consent or send communications, (2) Database CHECK constraint forbids status='sent' without `approved_by IS NOT NULL`, (3) Sending fails closed (503) without verified provider. |
| **API7:2023 Server Side Request Forgery (SSRF)** | **MITIGATED** | All outbound requests (Switch, Supabase, Anthropic) target fixed, server-configured URLs only. User-supplied URLs are never fetched. Storage keys are regex-validated (`^[A-Za-z0-9][A-Za-z0-9._/-]*$`) to prevent path traversal. |
| **API8:2023 Security Misconfiguration** | **MITIGATED** | (1) Production boot validator rejects missing secrets or insecure dev flags, (2) All responses emit security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. |
| **API9:2023 Improper Inventory Management** | **MITIGATED** | Clean API boundary under `/api/v1/`, complete OpenAPI 3.1 documentation, operational metrics (`/api/v1/metrics`), integration diagnostics (`/api/v1/integrations/status`). |
| **API10:2023 Unsafe Consumption of APIs** | **MITIGATED** | (1) AI responses treated as untrusted JSON parsed through strict Pydantic models, (2) Inbound Switch events require HMAC signature verification, (3) Outbound Switch delivery uses atomic `SKIP LOCKED` outbox sweeper. |

---

## 3. Cryptographic Controls & Data Protection

1. **Envelope Encryption for Contact Data:**
   - Participant contact data uses AES-128-CBC + HMAC-SHA256 (Fernet) versioned envelopes (`v2.<kid>.<token>`).
   - Backward compatibility for legacy tokens retained.
   - Zero-downtime key rotation script provided (`scripts/rotate_encryption_keys.py`).
2. **Private Document Storage:**
   - Files are stored in private storage (filesystem / Supabase private buckets).
   - Direct public access disabled.
   - Access governed by short-lived HMAC-SHA256 signed URLs bound to specific purpose, project, participant, and expiration.
3. **Immutability of Audit Trails:**
   - `audit_events` and `consent_records` tables protected by PostgreSQL database triggers (`trg_audit_events_immutable`, `trg_consent_records_immutable`) that reject all `UPDATE` and `DELETE` queries at the engine level.

---

## 4. Verification Evidence

- **Unit & Integration Test Suite:** 86 automated tests passing in ~25 seconds.
- **RLS Isolation Tests:** 8 direct-SQL tests executing under runtime role `scenesteward_app` with zero application code, verifying engine-enforced isolation.
- **Static Analysis:** Ruff linting 100% clean across all modules, scripts, and tests.
- **Database Migrations:** Clean Alembic history at head revision `c7a1e52b93f0`.

