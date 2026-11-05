# SceneSteward — Final Security & Trust Boundary Report

**Date:** November 2026  
**Auditor:** Principal Application Security Engineer & PostgreSQL Security Auditor  
**Repository:** `nikhillakra2007-tech/SceneSteward`  

---

## 1. Threat Model & Security Posture

SceneSteward is engineered to operate under zero-trust assumptions regarding participant data, user input, external documents, and automated agents.

### 1.1 Threat Vectors & Mitigations

| Threat Vector | Severity | Architectural Mitigation | Verification Mechanism |
|:---|:---:|:---|:---|
| **SQL Injection / Parameter Tampering** | Critical | Parameterized SQLAlchemy queries; runtime execution restricted to unprivileged `scenesteward_app` role; RLS enforced on all tables. | `test_tenant_isolation.py`, `audit_adversarial_current.py` |
| **Session Role / Tenant Impersonation** | Critical | HMAC-SHA256 authenticated database triggers (`fn_enforce_identity_trust()`). Session claim tampering rejected instantly. | `audit_adversarial_current.py` |
| **Document Malware / Zip Bombs** | High | Multi-layer screening: preflight extension check, file size limits, decompression bomb verification, and ClamAV daemon antivirus scanning. | `test_malware_scanner.py` |
| **Prompt Injection via Uploaded Release Forms** | High | Sanitization of incoming text; regex neutralization of role prompts (`[SYSTEM]`, `ignore previous instructions`); stripping smuggled control chars. | `test_document_intelligence.py` |
| **Non-Transitive Consent Leakage** | Critical | Deterministic 15-category comparison engine; absolute isolation per category; silence strictly defaults to `UNRESOLVED` / `not_discussed`. | `test_consent_engine_matrix.py` (63 test cases) |
| **IDOR via Participant Portal** | High | Cryptographically signed HMAC-SHA256 portal tokens with 7-day TTL; validation against participant ID and project ID claims. | `test_tenant_isolation.py` |
| **Distributed Denial of Service (DoS)** | Medium | Sliding-window token bucket rate limiting via Redis with local in-memory fallback; proxy spoofing protection via trusted proxy resolution. | `test_rate_limiter.py` |

---

## 2. Row-Level Security & Cryptographic Boundary

All queries executed by the application run under the restricted role `scenesteward_app` (`NOBYPASSRLS`). The session variables `app.user_id` and `app.is_system` cannot be modified without providing a matching HMAC-SHA256 signature generated using the secret `DATABASE_IDENTITY_SECRET`.

Any unauthorized attempt to alter `app.user_id` triggers `fn_enforce_identity_trust()`, raising an exception and terminating the transaction immediately.

---

## 3. Cryptographic Storage of Sensitive Data

- Participant contact records (`phone`, `email`, `physical_address`) are encrypted at rest using Fernet symmetric encryption (`APP_ENCRYPTION_KEY`).
- Plaintext contact details never touch the PostgreSQL database tables, disk storage, application logs, or audit payloads.
- Key rotation scripts (`rotate_encryption_keys.py`) allow seamless key transitions with deterministic re-encryption.

---

## 4. Security Sign-Off

The security architecture of SceneSteward has been audited across all layers. Zero high or critical vulnerabilities remain unresolved. The platform is hardened for production operations.
