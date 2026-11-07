# SCENESTEWARD — TEST RESULTS & AUTOMATED VERIFICATION
**Document Reference:** `docs/TEST_RESULTS.md`  
**Execution Date:** 2026-11-06  
**Auditor:** QA & Reliability Engineering  

---

## 1. Test Suite Summary Table

| Test Suite / Tool | Command Executed | Total Tests | Passed | Failed | Skipped | Status | Execution Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Unit & Integration** | `& backend\.venv\Scripts\python.exe -m pytest backend/tests` | 293 | 293 | 0 | 0 | **PASS** | 80.46s |
| **Static Code Analysis** | `& backend\.venv\Scripts\python.exe -m ruff check backend` | N/A | Clean | 0 | 0 | **PASS** | 1.82s |
| **Documentary Lifecycle** | `& backend\.venv\Scripts\python.exe backend/scripts/verify_documentary_lifecycle.py` | 8 | 8 | 0 | 0 | **PASS** | 3.52s |
| **Frontend Production Build** | `npm --prefix frontend run build` | 6 routes | 6 | 0 | 0 | **PASS** | 24.12s |
| **Playwright Browser E2E** | `npx @playwright/test test frontend/e2e/comprehensive_product_experience.spec.ts` | 11 | 11 | 0 | 0 | **PASS** | 34.6s |
| **Deep Invariant Validation** | `& backend\.venv\Scripts\python.exe scratch/verify_all_workflows.py` | 8 workflows | 8 | 0 | 0 | **PASS** | 2.14s |

---

## 2. Detailed Execution Results

### A. Pytest Backend Suite (293 / 293 Passed)
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.3, pluggy-1.5.0
rootdir: C:\Users\nikhi\OneDrive\Desktop\coding\FLIPTHESWITCH\backend
plugins: anyio-4.6.2.post1, asyncio-0.24.0
collected 293 items

backend/tests/unit/test_agents.py .........................             [  8%]
backend/tests/unit/test_analytics.py ................................... [ 20%]
backend/tests/unit/test_auth.py .................                       [ 26%]
backend/tests/unit/test_consent.py ..................................... [ 39%]
backend/tests/integration/test_api_endpoints.py ....................... [ 47%]
backend/tests/integration/test_database_rls.py ........................ [ 55%]
backend/tests/integration/test_reviews.py .............................. [ 65%]
backend/tests/integration/test_communications.py ....................... [ 73%]
backend/tests/security/test_production_hardening.py .................... [ 80%]
backend/tests/security/test_trust_boundaries.py ........................ [ 88%]
backend/tests/workflows/test_lifecycle_stages.py ....................... [ 96%]
backend/tests/workflows/test_revocation_cascades.py ............        [100%]

============================= 293 passed in 80.46s =============================
```

### B. Documentary Lifecycle Verification (8 / 8 Stages Passed)
```text
===========================================================================
 SceneSteward — 8-Step Documentary Lifecycle Verification
 Environment: TEST | Python: 3.12.10
===========================================================================
[Step 1/8] Director Authentication & Project Workspace Initialization... [OK]
[Step 2/8] Participant Registration in PostgreSQL...................... [OK]
[Step 3/8] 15 Canonical Categories of Consent Recorded & Confirmed..... [OK]
[Step 4/8] Proposed Footage / Likeness Use Submission.................. [OK]
[Step 5/8] SceneSteward Invariant & Automated Comparison Engine........ [OK]
[Step 6/8] Advisory Agent Guidance & Human Review Decision Gate........ [OK]
[Step 7/8] Participant Care Communication & Outbound Fail-Closed Gate... [OK]
[Step 8/8] Cryptographic Participant Transparency Portal & Audit Trail. [OK]

SCENESTEWARD VERIFICATION SUMMARY: 8/8 STEPS PASSED
```

### C. Playwright Browser E2E Suite (11 / 11 Passed)
```text
Running 11 tests using 1 worker

  ok  1 Test A — Authentication flow, form validation, and session management (5.2s)
  ok  2 Test B — Navigation links, active state indicators, and mobile drawer (8.1s)
  ok  3 Test C — Projects workspace, search filtering, and workspace navigation (715ms)
  ok  4 Test D — Participant roster, language options, and portal access (904ms)
  ok  5 Test E — Canonical 15 categories, non-transitive invariants, and choice badges (697ms)
  ok  6 Test F — Advisory disclaimer and mandatory human decision rationale (2.3s)
  ok  7 Test G — Formal withdrawal warning and submission interface (650ms)
  ok  8 Test H — Analytics dashboard, KPI cards, category breakdown, and export dialog (1.7s)
  ok  9 Test I — Switching between preset personas refreshes header identity (1.4s)
  ok 10 Test J — Responsive rendering across Mobile, Tablet, and Desktop viewports (2.9s)
  ok 11 Test K — Handles non-existent routes and records gracefully (616ms)

  11 passed (34.6s)
```

### D. Next.js Production Build
```text
Route (app)                              Size     First Load JS
┌ ○ /                                    5.14 kB         103 kB
├ ○ /_not-found                          873 B          88.2 kB
├ ○ /analytics                           11 kB           108 kB
├ ƒ /participant/[id]                    6.58 kB         107 kB
├ ○ /projects                            3.33 kB         104 kB
└ ƒ /projects/[id]                       11.7 kB         113 kB
+ First Load JS shared by all            87.3 kB

Compiled successfully. 0 TypeScript errors. 0 Lint errors.
```

