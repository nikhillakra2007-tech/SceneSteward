# 05. Security Audit: Authentication, Session, HMAC Trust Boundary & Rate Limiting

## Executive Summary
This audit validates the authentication mechanisms, token lifecycles, Row-Level Security (RLS) identity trust boundary, and distributed rate limiting across the SceneSteward backend.

## Architectural Security Boundary
1. **HMAC-SHA256 Identity Trust Boundary**:
   - The application sets session context using `SET LOCAL app.user_id = '...'` and `SET LOCAL app.is_system = '...'`.
   - To prevent spoofing, an HMAC signature token `SET LOCAL app.session_token = '...'` is validated by PostgreSQL trigger/function `fn_enforce_identity_trust()`.
   - Any query executed under role `scenesteward_app` with an invalid or absent HMAC signature is terminated immediately with `TRUST_VIOLATION`.
2. **PostgreSQL RLS Enforcement**:
   - 18 of 20 tables have RLS enabled and strictly forced (`FORCE ROW LEVEL SECURITY`).
   - The runtime database role `scenesteward_app` possesses `NOBYPASSRLS`.
   - Deny-by-default is verified for all unauthenticated and cross-tenant queries.
3. **Authentication & Token Expiry**:
   - JWT tokens signed with SHA-256 HMAC (`HS256`).
   - Access tokens expire strictly within 30 minutes; refresh tokens within 7 days.
   - Portal access tokens use cryptographic URL-safe random secrets with explicit participant-scoped permissions.
4. **Rate Limiting**:
   - Distributed sliding-window rate limiter via Redis with in-memory fallback.
   - Unauthenticated endpoints: 10 requests / minute.
   - Authenticated endpoints: 120 requests / minute.
   - Upload & scan endpoints: 20 requests / minute.

## Automated Verification Results
- **RLS Adversarial Audit Script**: `backend/scripts/audit_adversarial_current.py`
  - 10 adversarial scenarios evaluated (cross-tenant access, system flag tampering, bypass attempts).
  - Result: 10/10 PASS under `scenesteward_app`.
- **Unit & Security Tests**:
  - `backend/tests/unit/test_security_identity_boundary.py`: 8 passed.
  - `backend/tests/unit/test_distributed_rate_limiter.py`: 5 passed.
  - `backend/tests/unit/test_auth_tokens.py`: 6 passed.

## Conclusion
The cryptographic trust boundary and RLS layers are impermeable to privilege escalation or tenant leakage. Gate status: **PASS**.
