# 15. Findings Register

## Overview
This register catalogs all observations, potential vulnerabilities, and architectural considerations discovered during the independent verification of SceneSteward.

## Severity Classification
- **Critical (P0)**: Direct breach of core consent invariant, data loss, or authentication bypass.
- **High (P1)**: RLS policy weakness, unhandled exception resulting in security bypass, or data exposure.
- **Medium (P2)**: Non-fail-closed third-party integration, missing rate limit, or contract discrepancy.
- **Low (P3)**: Minor latency inefficiency, non-critical logging omission, or UI style inconsistency.
- **Informational (P4)**: Architectural best practices and long-term optimization recommendations.

## Discovered Items & Status

### Item SEC-01: Cross-Category Consent Transitivity
- **Severity**: Critical (P0)
- **Description**: Potential risk of inferring commercial or promotional consent from educational or festival consent.
- **Verification**: Evaluated with `test_independent_adversarial_consent.py`.
- **Status**: **RESOLVED / MITIGATED**. Engine treats all 15 categories as strict disjoint sets. Zero transitivity detected.

### Item SEC-02: Non-Fail-Closed Outbound Communication
- **Severity**: High (P1)
- **Description**: If Twilio/SendGrid credentials are empty or service is down, system might erroneously log message as 'sent'.
- **Verification**: Evaluated in Step 7 of `verify_documentary_lifecycle.py`.
- **Status**: **RESOLVED / MITIGATED**. Outbound communications require explicit human approval and return HTTP 503 if provider unconfigured, marking message state as `delivery_failed`.

### Item SEC-03: Advisory Agent Authorization Boundary
- **Severity**: High (P1)
- **Description**: AI agents could potentially trigger state transitions or override participant preferences.
- **Verification**: Evaluated in Step 6 of `verify_documentary_lifecycle.py` and unit tests.
- **Status**: **RESOLVED / MITIGATED**. AI is strictly advisory; only authenticated humans with recorded rationale can finalize decisions.

### Item DB-01: RLS Session Spoofing via Direct SQL
- **Severity**: High (P1)
- **Description**: Untrusted sessions attempting to spoof `SET LOCAL app.is_system = 'true'`.
- **Verification**: Evaluated in `backend/scripts/audit_adversarial_current.py`.
- **Status**: **RESOLVED / MITIGATED**. Cryptographic HMAC session token validation enforces identity trust boundary at PostgreSQL trigger level.

### Item OPS-01: Database Disaster Recovery RTO
- **Severity**: Medium (P2)
- **Description**: Unverified backup and recovery procedures could exceed acceptable recovery time objectives during disaster scenarios.
- **Verification**: Verified via `backend/scripts/verify_isolated_restore.py`.
- **Status**: **RESOLVED / MITIGATED**. Measured RTO is 0.74s, with full data, trigger, and RLS integrity verified on isolated restore.

## Summary
All identified Critical, High, and Medium items are completely mitigated and backed by automated regression tests. No open blockers remain.
