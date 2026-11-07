# SCENESTEWARD — FINAL BACKEND AUDIT REPORT
## API Endpoints, Middleware, Service Contracts & Automated Test Results

**Date:** 2026-11-07  
**Runtime:** Python 3.12 / FastAPI / Uvicorn  
**Port:** `8000`  
**Test Suite:** Pytest — **310/310 PASS**  

---

## 1. API Route Inventory

| Router Prefix | Method | Endpoint | Description | Auth Requirement |
|---|---|---|---|---|
| `/health` | `GET` | `/health` | Application status probe | Public |
| `/api/v1/auth` | `POST` | `/login` | Issues JWT token for email/password | Public |
| `/api/v1/auth` | `GET` | `/me` | Returns active user profile | Bearer JWT |
| `/api/v1/auth` | `POST` | `/switch-persona` | Fast persona switching for demo/testing | Bearer JWT |
| `/api/v1/projects` | `GET` | `/` | Lists user's documentary projects | Bearer JWT |
| `/api/v1/projects` | `POST` | `/` | Creates new documentary project | Bearer JWT |
| `/api/v1/projects` | `GET` | `/{id}` | Fetches project by ID | Bearer JWT |
| `/api/v1/participants` | `GET` | `/` | Lists project participants | Bearer JWT |
| `/api/v1/participants` | `POST` | `/` | Registers new film participant | Bearer JWT |
| `/api/v1/participants` | `GET` | `/{id}/transparency-token` | Mints participant portal access token | Bearer JWT |
| `/api/v1/consent` | `POST` | `/records` | Creates formal consent record | Bearer JWT |
| `/api/v1/consent` | `GET` | `/{id}/matrix` | Returns 15-category consent breakdown | Bearer JWT / Portal Token |
| `/api/v1/reviews` | `GET` | `/` | Lists pending ethical review requests | Bearer JWT |
| `/api/v1/reviews` | `POST` | `/{id}/decision` | Commits decision with mandatory rationale | Bearer JWT (Producer/Director) |
| `/api/v1/communications`| `POST` | `/draft` | Drafts participant care email | Bearer JWT |
| `/api/v1/communications`| `POST` | `/{id}/send` | Delivers pre-cleared communication | Bearer JWT (Fail-closed 503) |
| `/api/v1/transparency` | `GET` | `/portal` | Participant self-service consent review | Portal Token |
| `/api/v1/transparency` | `POST` | `/withdraw` | Submits formal consent withdrawal | Portal Token |
| `/api/v1/analytics` | `GET` | `/overview` | Aggregated clearance KPIs | Bearer JWT |
| `/api/v1/analytics` | `GET` | `/export/csv` | Structured CSV audit export | Bearer JWT |
| `/api/v1/analytics` | `GET` | `/export/json` | Structured JSON audit export | Bearer JWT |

---

## 2. Test Execution Breakdown

All 310 backend tests pass with zero failures:

- **Unit Tests (112 tests):**
  - Consent engine matrix evaluations (63 tests)
  - Comparison engine (10 tests)
  - Encryption & security config (14 tests)
  - Rate limiting & health probes (14 tests)
  - Document intelligence & adversarial cases (11 tests)
- **Security & Authorization (77 tests):**
  - Ethical consent invariants (12 tests)
  - Lifecycle guards & trust boundaries (24 tests)
  - Operational resilience & production hardening (21 tests)
  - Role-based access control (10 tests)
  - Review decision boundaries & RLS isolation (17 tests)
  - Secret lifecycle (4 tests)
- **Integration & Workflows (121 tests):**
  - Switch multi-agent & protocol handling (12 tests)
  - Antigravity ACP handshake simulation (4 tests)
  - Document intelligence, extraction, and migration (23 tests)
  - Reporting, notifications, communications (7 tests)
  - Staging end-to-end acceptance (9 tests)
  - Authentication, failure modes, metrics (20 tests)
  - Full documentary life cycles & tenant isolation (46 tests)

