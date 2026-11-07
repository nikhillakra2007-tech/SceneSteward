# SCENESTEWARD — ENGINEERING AUDIT REPORT
**Document Reference:** `docs/ENGINEERING_AUDIT_REPORT.md`  
**Execution Date:** 2026-11-06  
**Auditor:** Principal Software & Security Engineering Review  
**Commit Inspected:** `f01a9be4460f207c72ffc55bd85c0dbc073cb95a`  
**Target Environment:** Local Workstation (Windows 11 / Python 3.12.10 / Node.js v24.18.1 / PostgreSQL 18)

---

## 1. Initial Repository Assessment & Inventory

An independent audit was conducted across the SceneSteward codebase without relying on previous narrative summaries. 

### Core Tech Stack
- **Backend Framework:** FastAPI 0.115+ (Python 3.12.10), SQLAlchemy 2.0 (psycopg v3 sync driver), Alembic 1.13+.
- **Frontend Architecture:** Next.js 14.2.35 (React 18.3.1, TypeScript 5.6.3, Tailwind CSS 3.4.17, Lucide-React).
- **Database Engine:** PostgreSQL 18 with active Row Level Security (RLS) policies on core multi-tenant tables.
- **Testing Architecture:** Pytest 8.3+, FastAPI TestClient, Playwright 1.65.0.

### Public Database Tables Verified
Direct database connection verified 19 public tables with real persisted records:
1. `users` (30 rows)
2. `projects` (15 rows)
3. `project_memberships` (30 rows)
4. `participants` (11 rows)
5. `consent_records` (11 rows)
6. `consent_choices` (113 rows)
7. `proposed_uses` (10 rows)
8. `proposed_use_analyses` (7 rows)
9. `reviews` (8 rows)
10. `tasks` (22 rows)
11. `participant_communications` (14 rows)
12. `participant_contact_records` (1 row)
13. `audit_events` (147 rows)
14. `agent_runs` (35 rows)
15. `story_elements` (4 rows)
16. `release_documents` (0 rows)
17. `release_document_pages` (0 rows)
18. `switch_room_links` (0 rows)
19. `integration_events` (0 rows)

---

## 2. Architecture & Trust Boundary Findings

### A. Database Trust Boundary & RLS (Status: VERIFIED)
- **Role Separation:** The application runtime connection uses the non-owner role (`scenesteward_app`).
- **Least Privilege:** When executing queries on administrative tables like `alembic_version`, PostgreSQL correctly returned `permission denied for table alembic_version`. This proves that schema owner rights cannot be usurped by application runtime SQL injection.
- **Tenant Isolation:** Multi-tenant RLS requires transaction-local session state (`app.user_id` with HMAC signature `app.user_sig` or trusted `app.system`). Sessions lacking valid identity see zero rows (deny by default).

### B. Ethical Invariants Enforcement (Status: VERIFIED)
- **Silence is Never Consent:** Unrecorded or omitted categories default to `not_discussed`. In `POST /api/v1/projects/{id}/proposed-uses`, when `promotional_clips` was requested for a subject whose release only granted `documentary_appearance`, the engine flagged the discrepancy and blocked automated clearance.
- **Non-Transitivity:** Agreement to documentary appearance does not imply promotional use or AI voice cloning.
- **Advisory Agent Boundary:** AI agents provide advisory suggestions only. AI agents cannot approve or decline uses.
- **Mandatory Human Rationale Gate:** Submitting a review decision with an empty rationale (`reason=""`) was rejected by the backend with HTTP `422 Unprocessable Entity`.
- **State Machine Immutability:** Attempting a second decision on an already decided review failed with HTTP `409 Conflict`.

### C. Participant Care & Outbound Communications (Status: VERIFIED)
- **Gate Enforcement:** Attempting to dispatch an unapproved draft message via `POST /api/v1/communications/{id}/send` failed with HTTP `412 Precondition Failed`.
- **Fail-Closed Delivery:** In an environment without external SMTP/Twilio configuration, calling `send` on an approved message returned HTTP `503 Service Unavailable` with `no_provider_configured`. The system safely fail-closed and did NOT record a false "Sent" state.

---

## 3. Frontend Architecture Findings

### A. Authentication & Personas (Status: VERIFIED - DEVELOPMENT CONVENIENCE)
- The header quick-login buttons (`Olivia Director`, `Claire Care`, `Marcus Producer`, `Elena Legal`) call `/api/v1/auth/dev-token` to mint a valid RS256/HS256 JWT bearer token from the backend.
- **Honest Finding:** This dev-login flow is enabled only when `APP_ENV=development` or `APP_ENV=test` and `AUTH_PROVIDER=dev`. In production (`APP_ENV=production`), `POST /api/v1/auth/dev-token` is disabled and returns `403 Permission Denied`. Production deployments require the configured OAuth/Supabase JWKS provider.

### B. Route Inventory & Render Behavior
- `/` — Static landing page, platform principles, and entry button.
- `/projects` — Real-time search filter across project titles, descriptions, and themes.
- `/projects/[id]` — Project workspace containing 5 dynamic tabs: Roster, Intake, Review, Care, Audit.
- `/analytics` — Aggregates metrics from `/api/v1/analytics/*`, displays SVG charts, and provides CSV/JSON exports.
- `/participant/[id]` — Public transparency portal authenticated via cryptographically signed participant tokens.

---

## 4. Identified Defects & Applied Fixes

### Issue 1: Playwright E2E Suite Selector Mismatch (Severity: P2 - FIXED)
- **Symptom:** Playwright E2E Test A timed out attempting to click `[data-testid="quick-login-olivia"]` while the authentication modal backdrop was open.
- **Root Cause:** In `comprehensive_product_experience.spec.ts`, the script re-opened the modal and attempted to click an element behind the backdrop overlay instead of clicking the preset inside the modal (`button:has-text("olivia@example.com")`).
- **Fix:** Corrected test selector to target the preset button within the active dialog, verified modal closure and identity persistence.

### Issue 2: Analytics Tab Selector Label (Severity: P3 - FIXED)
- **Symptom:** E2E Test H failed looking for `button:has-text("AI Advisory & Trends")`.
- **Root Cause:** The actual button text in `frontend/src/app/analytics/page.tsx` is `"Advisory & Trends"`.
- **Fix:** Aligned the test locator in `comprehensive_product_experience.spec.ts` with the actual DOM text.

---

## 5. Verification Status by Subsystem

| Subsystem | Status | Verification Method |
| :--- | :--- | :--- |
| **PostgreSQL Database** | **VERIFIED** | Direct Python script via psycopg/SQLAlchemy with 19 public tables inspected |
| **FastAPI Backend Core** | **VERIFIED** | 293 unit/integration tests passed in 80.46s; health endpoint active |
| **Authentication & RBAC** | **VERIFIED** | Dev token exchange, identity inspection (`/auth/me`), invalid token rejection |
| **Documentary Lifecycle** | **VERIFIED** | 8/8 stages executed end-to-end via `verify_documentary_lifecycle.py` |
| **Consent Evaluation Engine** | **VERIFIED** | Non-transitive 15-category evaluation; silence-is-never-consent verified |
| **Human Review Gate** | **VERIFIED** | Empty rationale rejected (422); duplicate decision rejected (409) |
| **Participant Care Outreach** | **VERIFIED** | Unapproved send blocked (412); offline provider fail-closed (503) |
| **Transparency Portal** | **VERIFIED** | Token-authenticated portal access verified under RLS boundary |
| **Analytics Engine & Exports** | **VERIFIED** | Overview KPI API, JSON export, and CSV export validated |
| **Next.js Frontend Build** | **VERIFIED** | Production build compiled cleanly with 0 errors across all 6 routes |
| **Playwright Browser Tests** | **VERIFIED** | 11/11 tests passed in 34.6s against live local server |

---

## 6. Remaining Limitations

1. **Document OCR Pipeline:** Uploading binary PDF files for OCR extraction requires `tesseract` and ClamAV daemon. In local environments lacking system tesseract binaries, OCR extraction falls back to plain-text extraction or placeholder status.
2. **External Email / SMS Delivery:** Outbound communications safely fail-closed (HTTP 503) when SMTP/Twilio credentials are absent. The UI provides a 1-click clipboard copy action to allow coordinators to send verified text manually.

