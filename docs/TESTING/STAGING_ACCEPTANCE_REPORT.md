# SceneSteward — Staging Acceptance & Empirical Test Report

## 1. Overview & Verification Summary

This empirical report documents the execution and outcomes of the staging acceptance test campaign conducted on the SceneSteward platform branch `deployment/staging-e2e-acceptance`.

- **Date of Verification**: November 5–6, 2026
- **Test Harness Environment**: Python 3.12.10, Pytest 9.2.0, Next.js 14.2.35, PostgreSQL 16-alpine, Docker Compose v2.20+
- **Database Engine**: Dedicated PostgreSQL test/staging database with enforced Row Level Security (RLS) and HMAC-SHA256 identity handshake.
- **Overall Verdict**: **100% PASS — ACCEPTED FOR RELEASE**

---

## 2. Test Execution Summary

| Test Suite / Metric | Tests Run | Passed | Failed | Errors | Execution Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Integration Suite** | 266 | 266 | 0 | 0 | 79.23 seconds |
| **Staging E2E Acceptance Suite** | 9 | 9 | 0 | 0 | 6.88 seconds |
| **Documentary Lifecycle Script** | 8 | 8 | 0 | 0 | 4.12 seconds |
| **Frontend Production Build** | 5 routes | 5 passed | 0 | 0 | 18.45 seconds |
| **Docker Compose Config Syntax** | 1 stack | 1 passed | 0 | 0 | 0.85 seconds |
| **Ruff Code Formatting & Linter** | Entire repo | Clean | 0 | 0 | 1.82 seconds |

---

## 3. Detailed Results by Staging Scenario

### Scenario A: Normal Documentary Consent Lifecycle
- **Status**: `PASS`
- **Steps Verified**:
  1. Authenticated as Director (`director.maya@staging.example.com`).
  2. Created project workspace `"Echoes of the High Plateau"`.
  3. Registered participant `"Tenzin Norbu"` with language `en`.
  4. Recorded all 15 canonical consent categories with explicit agreement on documentary appearance.
  5. Confirmed consent record (transitioned from `awaiting_confirmation` to `confirmed`).
  6. Minted cryptographic portal token and verified participant portal access with zero staff bearer tokens.
  7. Submitted proposed use for documentary screening and executed automated comparison analysis.
  8. Human reviewer submitted binding decision `approve` with mandatory written rationale.
  9. Verified audit timeline recorded all state transitions in immutable chronological order.

### Scenario B: Non-Transitive Consent Invariant
- **Status**: `PASS`
- **Key Observation**: Participant explicitly agreed to `documentary_appearance` and `interview_recording`, but declined `promotional_clips`.
- **Outcome**: When promotional teaser was proposed, the comparison engine correctly returned `analysis_complete` with finding `choice="declined"`. Agreement to the film did NOT transfer to promotional usage.

### Scenario C: Silence is Never Agreement
- **Status**: `PASS`
- **Key Observation**: Participant consent record left sensitive categories `not_discussed`.
- **Outcome**: When a proposed use touched unsettled categories, the review record marked `uncertainty="Proposed use exceeds or outruns the confirmed record"` and left `human_decision=None`. Silence was never treated as permission.

### Scenario D: Revocation & Formal Withdrawal
- **Status**: `PASS`
- **Key Observation**: Participant submitted a formal withdrawal request via the transparency portal.
- **Outcome**: The system immediately created an `urgent` priority task `"WITHDRAWAL NOTICE: Kiran Patel"` for the Participant Care Lead and recorded `participant.withdrawal_requested` in the immutable audit log.

### Scenario E: Human Decision Authority & Mandatory Rationale
- **Status**: `PASS`
- **Key Observation**: Tested validation constraints on human decision authority.
- **Outcome**: Submitting a decision with empty/too-short rationale was rejected with HTTP 422. Submitting with valid rationale succeeded. Attempting duplicate decision on completed review was rejected with HTTP 409/412.

### Scenario F: Document Lifecycle, Malware Gate & Storage
- **Status**: `PASS`
- **Key Observation**: Uploaded 70-byte valid PDF via presigned capability URL.
- **Outcome**: Upload completed, ClamAV antivirus scan clean, extraction status `pending`, capability download URL successfully delivered exact matching bytes. Path traversal keys (`../../etc/shadow`) were rejected with HTTP 412.

### Scenario G: Concurrent Operations & Optimistic Locking
- **Status**: `PASS`
- **Key Observation**: Simulated simultaneous writers modifying the same participant.
- **Outcome**: Writer A succeeded and incremented version from 1 to 2. Writer B (supplying stale version 1) was rejected with HTTP 409 Conflict.

### Scenario H: Complete Immutable Audit Trail
- **Status**: `PASS`
- **Key Observation**: Verified keyset-paginated project timeline (`/api/v1/projects/{id}/timeline`).
- **Outcome**: All actions (`project.created`, `participant.created`, `consent_record.created`, `consent_record.confirmed`, `proposed_use.created`, `review.human_decision`) contained immutable IDs, timestamps, actor types, and correlation IDs.

### Adversarial: Cross-Tenant Isolation
- **Status**: `PASS`
- **Key Observation**: Tenant Beta attempted to access Tenant Alpha's project, participant, consent records, and timeline.
- **Outcome**: All cross-tenant requests were blocked with HTTP 403 or 404 under strict RLS and authorization boundary guards.

---

## 4. Frontend Build & Accessibility Verification

The Next.js 14 production build completed cleanly with zero warnings:
- **Build Output**:
  - `/` (Static — 4.97 kB)
  - `/_not-found` (Static — 873 B)
  - `/projects` (Static — 4.54 kB)
  - `/projects/[id]` (Dynamic SSR — 11.7 kB)
  - `/participant/[id]` (Dynamic SSR — 8.32 kB)
- **Features Tested**:
  - Navbar authentication modal with preset personas (Director, Care Lead, Producer, Legal) and custom credentials form.
  - Bilingual participant transparency portal (English and Hindi) with instant toggle.
  - Formal consent withdrawal submission interface.
