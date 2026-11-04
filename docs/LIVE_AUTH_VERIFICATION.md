# SceneSteward — Live Supabase Auth Staging Activation Report

**Date**: November 4, 2026  
**Auditor**: Application Security Reviewer & Backend Integration Engineer  
**Subsystem**: Supabase Auth / JWKS JWT Verification Layer  
**Current Verification State**: **`CREDENTIALS PENDING (BLOCKED LIVE)`**  

---

## 1. Technical Requirements & Invariants

SceneSteward uses JSON Web Tokens (JWT) issued by Supabase Auth with RS256 or ES256 asymmetric cryptographic signatures.
The validation layer (`backend/app/core/security.py`) enforces:
1. **JWKS Fetching & Caching**: Public keys are loaded dynamically from `/auth/v1/.well-known/jwks.json` using `jwt.PyJWKClient` (cached with a 1-hour TTL).
2. **Issuer Verification**: `iss` claim must match `SUPABASE_URL/auth/v1`.
3. **Audience Verification**: `aud` claim must match `authenticated` (or `AUTH_AUDIENCE`).
4. **Signature Authenticity**: Unsigned tokens, forged keys, or algorithm mismatches (e.g. HS256 algorithm confusion) are immediately rejected with HTTP 401.
5. **Token Expiration**: Expired tokens fail with `token_expired` error code.
6. **No Dev Tokens in Production/Staging**: Dev HS256 tokens are strictly forbidden when `APP_ENV=production`.

---

## 2. Test Execution & Diagnostic Output

### Local & Synthetic Verification
- **Automated Tests**:
  - `backend/tests/integration/test_auth.py`
  - 12/12 passing tests including:
    - `test_missing_token` -> HTTP 401
    - `test_garbage_token` -> HTTP 401
    - `test_expired_token` -> HTTP 401
    - `test_wrong_audience` -> HTTP 401
    - `test_wrong_issuer` -> HTTP 401
    - `test_tampered_signature` -> HTTP 401
    - `test_supabase_jwks_offline_verification` -> Synthetic RSA keypair test passed.

### Live Staging Probe Execution
- **Command**:
  ```powershell
  $env:PYTHONPATH = "backend"
  .\backend\.venv\Scripts\python.exe backend/scripts/verify_staging_auth.py
  ```
- **Actual Terminal Output**:
  ```
  ============================================================
  SceneSteward — Staging Auth Provider Verification
  ============================================================
  Configured Auth Provider: dev
  Staging JWKS URL: <unconfigured>
  Expected Issuer: scenesteward-dev
  Expected Audience: scenesteward-api

  [RESULT] BLOCKED: AUTH_PROVIDER is not 'supabase' or SUPABASE_URL / AUTH_JWKS_URL is not set.
  ```

---

## 3. Classification & Next Actions

- **Current State**: `MOCK TESTED / CREDENTIALS PENDING (BLOCKED LIVE)`
- **Remediation Steps**:
  1. Create a dedicated Supabase staging project.
  2. In `backend/.env.staging`:
     ```env
     AUTH_PROVIDER=supabase
     SUPABASE_URL=https://<your-project-ref>.supabase.co
     SUPABASE_ANON_KEY=<anon-key>
     AUTH_JWKS_URL=https://<your-project-ref>.supabase.co/auth/v1/.well-known/jwks.json
     AUTH_ISSUER=https://<your-project-ref>.supabase.co/auth/v1
     AUTH_AUDIENCE=authenticated
     ```
  3. Re-run `python backend/scripts/verify_staging_auth.py`.

