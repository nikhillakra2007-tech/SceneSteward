# SceneSteward — Phase 2 Implementation & System Audit

**Date:** November 2026  
**Auditor:** Principal Software Architect, Senior Backend/Frontend Engineer, DevSecOps & QA Lead  
**Repository:** `nikhillakra2007-tech/SceneSteward`  
**Target Milestone:** Full End-to-End Integration, Database Hardening, Authorization & Production Readiness  

---

## 1. Executive Summary & Verification Baseline

Before initiating Phase 2 development, the complete repository was independently inspected and re-verified:

- **Backend Pytest Suite:** Re-executed against the local test harness — **184 passed in 198.64s** (0 failures, 100% clean).
- **Backend Linting:** Executed `ruff check backend` — **All checks passed** (0 errors, 0 warnings).
- **Frontend Build:** Executed `npm run build` in `frontend/` — **Next.js 14.2.35 production build compiled successfully** across all static and dynamic routes (`/`, `/_not-found`, `/participant/[id]`, `/projects`, `/projects/[id]`).
- **Docker Compose Staging:** Executed `docker compose -f docker-compose.staging.yml config` — **100% valid configuration**, zero environment interpolation errors.
- **Git State:** `develop` and `main` branches are synchronized with origin at commit `78e27e8`.

---

## 2. Existing Functionality

The following foundational systems are implemented, tested, and operational:

1. **Security & Database Trust Boundary:**
   - PostgreSQL 18.6 with 4 Alembic migrations establishing 20 tables.
   - HMAC-SHA256 session claim trust boundary (`fn_enforce_identity_trust()` trigger) preventing role spoofing.
   - 18 project-scoped tables protected by PostgreSQL Row-Level Security (RLS) under the restricted `scenesteward_app` role.
   - Composite foreign-key constraints `(project_id, participant_id)` preventing cross-tenant leakage.

2. **Deterministic Consent Comparison Engine:**
   - 15 canonical categories independently evaluated:
     1. `interview_recording`
     2. `documentary_appearance`
     3. `name_identification`
     4. `face_identification`
     5. `sensitive_personal_details`
     6. `promotional_clips`
     7. `festival_submissions`
     8. `ai_transcription`
     9. `voice_cloning`
     10. `synthetic_likeness`
     11. `third_party_ai_processing`
     12. `new_audience`
     13. `new_territory`
     14. `new_platform`
     15. `new_story_context`
   - Core invariant enforced: *"A participant's agreement to one use must never automatically become agreement to another use. Silence is never agreement."*
   - Exhaustive 63-case unit test matrix (`test_consent_engine_matrix.py`).

3. **Protection & Storage Infrastructure:**
   - Distributed Redis sliding-window rate limiting with in-memory fallback (`app/core/rate_limiter.py`).
   - Anti-spoofing client IP resolution with right-to-left `X-Forwarded-For` traversal for trusted proxies.
   - Antivirus scanning with ClamAV fail-closed validation and decompression bomb prevention.
   - Transactional outbox sweeper (`scripts/switch_retry.py`) for Switch room integration.

4. **Frontend Foundation:**
   - Next.js 14, React 18, TypeScript, Tailwind CSS with tabbed Production Team Workspace and Participant Portal.

---

## 3. Incomplete Functionality & Gaps

1. **Participant Portal Authentication (IDOR Risk):**
   - Currently, `/participant/[id]` accepts any participant UUID in the route.
   - If a user navigates to `/participant/{uuid}`, there is no token or session check restricting access strictly to that participant or the authorized production staff.
   - *Requirement:* Implement cryptographic access tokens (magic link tokens) with expiration and rate limits for participant self-service access.

2. **Document Upload Lifecycle:**
   - While backend signed URLs exist (`/participants/{id}/documents/upload-url` and `complete-upload`), the frontend was pointing to `/projects/{id}/documents/upload-url`, causing 404s.
   - The frontend lacks a direct file-picker-to-storage-upload pipeline for documentary release forms and agreements.

3. **Participant Clarification to Care Workflow:**
   - In the Participant Portal, submitting a concern or clarification request does not currently persist to an API endpoint; it only sets local state.
   - *Requirement:* Implement `POST /participants/{id}/clarification-requests` to create an actionable care task and an immutable audit event.

4. **Project-Wide Document Roster:**
   - Document listing was only available on a per-participant endpoint (`/participants/{id}/documents`). Production teams require a project-level document query (`/projects/{id}/documents`) to audit all executed agreements in one workspace.

---

## 4. Broken Integrations & Schema Mismatches

Detailed audit of frontend TypeScript client (`frontend/src/lib/api.ts`) vs. backend FastAPI schemas (`backend/app/schemas/`):

| Entity / Action | Frontend (api.ts) | Backend FastAPI Schema | Defect / Impact |
|:---|:---|:---|:---|
| **Document Upload URL** | `POST /projects/{id}/documents/upload-url` | `POST /participants/{id}/documents/upload-url` | **404 Not Found**. Path mismatch. |
| **Document Listing** | `GET /projects/{id}/documents` | `GET /participants/{id}/documents` | **404 Not Found**. No project-level endpoint existed. |
| **Consent Creation** | `choices: Record<string, { choice: string }>` | `choices: list[ConsentChoiceIn]` | **422 Unprocessable Entity**. Array expected, object passed. |
| **Canonical Categories** | Used placeholders (`interview_inclusion`, `likeness_display`) | Canonical 15 categories (`interview_recording`, `documentary_appearance`, etc.) | **Validation Error**. Non-canonical category naming. |
| **Human Decision Enum** | `"approved"`, `"rejected"` | `"approve"`, `"decline"`, `"request_changes"`, `"needs_participant_discussion"` | **422 Unprocessable Entity**. Enum mismatch. |
| **Communication Approval** | `{ expected_version: number }` | `{ notes: str \| None }` | **422 Unprocessable Entity**. Payload field mismatch. |
| **Communication Fields** | `channel`, `body`, `status` | `communication_type`, `draft_content`, `communication_status` | **Field Name Mismatch**. UI cannot render received comms. |
| **Participant Status** | `status` | `participant_status` | **Field Name Mismatch**. Status renders as undefined. |

---

## 5. Database Architecture & Multi-Tenancy

- **Current Isolation Model:** Project-level isolation (`project_id`). Every entity (`participants`, `consent_records`, `proposed_uses`, `reviews`, `tasks`, `documents`, `communications`) has a mandatory `project_id` foreign key.
- **PostgreSQL RLS:** 18 tables enforce `project_id = ANY (SELECT project_id FROM project_memberships WHERE user_id = current_user_id() AND membership_status = 'active')`.
- **Identity Trust:** The DB trigger `fn_enforce_identity_trust()` prevents a malicious user from overriding `request.jwt.claim.sub` without possessing the server-side HMAC secret.
- **Tenant Isolation Verification:** Needs explicit integration test proving that a user belonging to Project A cannot read or write data in Project B, even if they guess valid UUIDs.

---

## 6. Authentication & Authorization Security Model

1. **Authentication Providers:**
   - `AUTH_PROVIDER=dev`: Issues HS256 tokens signed with `AUTH_DEV_SECRET`. Safe for local development and test automation.
   - `AUTH_PROVIDER=supabase`: Validates RS256 JWTs against JWKS endpoint.
2. **Role-Based Access Control (RBAC):**
   - `project_owner`, `producer`: Full administrative control, participant creation, consent confirmation, review decision, communication approval.
   - `participant_care_lead`: Participant management, consent recording/confirmation, task updates, communication drafting & approval.
   - `director`, `editor`: Story elements, proposed uses, reading participants and reviews.
   - `participant`: Restricted to self-record via `participant.user_id == user.id`.
3. **Participant Portal Security (Token Authentication):**
   - Need a dedicated cryptographic invitation/access token system (`ParticipantAccessToken`) so participants without full user accounts can securely view their record and submit feedback.

---

## 7. Business Workflows & Consent Invariant Status

1. **Silence is Never Agreement:** Verified in consent comparison engine (`test_consent_engine_matrix.py`).
2. **Per-Use Scope:** Verified that `interview_recording` agreement does not authorize `promotional_clips`, `voice_cloning`, or `synthetic_likeness`.
3. **Human Decision Guard:** AI agents emit findings (`AgentRun`), but only human staff can transition a review to `completed` with a binding decision (`approve` / `decline`).
4. **Communication Approval Guard:** Database CHECK constraint `ck_comms_sent_requires_approval` enforces that `communication_status = 'sent'` requires `approved_by IS NOT NULL AND sent_at IS NOT NULL`.

---

## 8. Prioritized Implementation Roadmap

### Phase 2A — Audit & Groundwork (Completed)
- Run baseline verifications (Pytest, Ruff, Next.js build, Docker Compose).
- Document all schema mismatches, missing endpoints, and security gaps in `docs/PHASE_2_IMPLEMENTATION_AUDIT.md`.

### Phase 2B — Database & Backend API Completion (`feat/api-workflow-completion`)
1. Add `GET /projects/{project_id}/documents` endpoint so production teams can view all project documents.
2. Add `POST /participants/{participant_id}/clarification-requests` endpoint to persist participant concerns as care tasks and audit events.
3. Add participant access token generation and verification endpoints (`POST /participants/{id}/access-token` and `GET /participant-portal/verify`).
4. Add automated multi-tenant cross-project isolation integration tests.

### Phase 2C — Frontend Contract & Workflow Integration (`feat/frontend-schema-integration`)
1. Align `frontend/src/lib/api.ts` with exact backend schemas:
   - Canonical 15 categories matching `app.core.choices.CONSENT_CATEGORIES`.
   - `choices: list[ConsentChoiceIn]` structure for consent recording.
   - `HumanDecisionRequest` with `"approve"`, `"decline"`, `"request_changes"`, `"needs_participant_discussion"`.
   - `CommunicationOut` with `communication_type`, `draft_content`, `communication_status`.
   - `ParticipantOut` with `participant_status`.
2. Connect document upload flow in UI: upload file via signed URL, complete upload, trigger ClamAV scan and OCR extraction.
3. Connect participant feedback form to `POST /participants/{id}/clarification-requests`.
4. Add participant access token verification to `/participant/[id]`.

### Phase 2D — Comprehensive End-to-End Workflow Verification (`test/full-lifecycle-verification`)
1. Create executable end-to-end integration test verifying the complete 8-step product journey:
   Director Login &rarr; Participant Added &rarr; 15-Category Consent Recorded &rarr; Footage Use Proposed &rarr; Comparison Evaluated &rarr; Human Review Decision Recorded &rarr; Participant Communication Drafted & Approved &rarr; Audit Trail Verified.
2. Verify without manual database edits or bypasses.

### Phase 2E — CI/CD & Deployment Hardening (`chore/ci-deployment-hardening`)
1. Update GitHub Actions workflow to run the complete expanded test suite.
2. Verify Docker staging build and container startup.

### Phase 2F — Production Release (`develop` &rarr; `main`)
1. Open Release PR to `main`.
2. Produce `docs/PHASE_2_COMPLETION_REPORT.md`.
