# SCENESTEWARD — FINAL SECURITY AUDIT REPORT
## Trust Boundaries, Invariant Enforcements, Least Privilege & Data Protection

**Date:** 2026-11-07  
**Scope:** Whole-system security evaluation (Backend, Switch Bridge, PostgreSQL, Transparency Portal)  
**Status:** PASS — Zero High or Critical Deficiencies  

---

## 1. Security Architecture & Trust Boundaries

```
[External World / Subject]
       │
       ▼ (HTTPS / TLS)
[Transparency Portal] ──(Scoped Portal Token)──► [RLS Policy Guard] ──► [PostgreSQL]
                                                        ▲
[Director / Producer]                                   │
       │                                                │
       ▼ (HTTPS / TLS)                                  │
[SceneSteward App] ────(JWT Bearer Token)───────────────┤
                                                        │
[Switch Platform] ─────(Switch Bearer Token)────────────┘
```

---

## 2. Invariant & Policy Verification

### 2.1 Mandatory Human Review Gate
- Consequential footage clearance actions (e.g. promoting raw interview clips to public broadcast trailers) cannot be automatically cleared by an AI agent or automated script.
- The backend rejects decision requests lacking written justification:
  - Missing rationale payload returns `HTTP 422 / 400`.
  - Empty or whitespace rationale string returns `HTTP 400 Bad Request`.
  - Once committed, review states cannot be overridden without a new review cycle (`HTTP 409 Conflict`).

### 2.2 Non-Transitive Consent Protection
- Standard production contracts often conflate initial filming releases with omnibus distribution rights.
- SceneSteward enforces 15 granular canonical categories:
  - `documentary_feature`
  - `promotional_clips`
  - `social_media_teasers`
  - `archival_syndication`
  - `educational_broadcast`
  - `theatrical_screening`
  - `streaming_vod`
  - `soundtrack_audio`
  - `still_photography`
  - `behind_the_scenes`
  - `festival_distribution`
  - `ai_model_training_exclusion`
  - `sensitive_biographical_disclosure`
  - `third_party_licensing`
  - `posthumous_use_window`
- Invariant: Consent in one category **never** implies consent in another. Silence or unaddressed categories default to `not_discussed`.

### 2.3 Cryptographic Audit Trail
- Every critical mutation produces an entry in `audit_events`.
- Events contain `event_type`, `actor_id`, `project_id`, `payload`, and a computed SHA-256 digest.
- PostgreSQL rules disallow updates or deletions on the `audit_events` table.

### 2.4 Fail-Closed Outbound Communication
- Outbound participant communications (e.g., notifying a subject of upcoming trailer usage) require prior human sign-off.
- If an email transport provider is unconfigured in development/staging environments, the delivery endpoint returns `HTTP 503 Service Unavailable` with a clear diagnostic code instead of fabricating a successful `sent` state.

### 2.5 Code Hygiene & Secret Management
- Zero active API keys or production database passwords are hardcoded in application source code.
- Environment variables are isolated via `.env` files that are strictly excluded in `.gitignore`.
- Ruff linter checks pass 100% cleanly with zero warnings or security rule suppressions.

