# SCENESTEWARD — LOCAL LAUNCH, LIVE BROWSER INSPECTION & DEMONSTRATION REPORT

**Date:** 2026-11-06  
**Application:** SceneSteward — Documentary Consent Management Platform  
**Target Environment:** Local Workstation (Windows 11 / Node.js v24.18.1 / Python 3.12.10 / PostgreSQL 18)  
**Status:** PASS — SERVICES ACTIVELY RUNNING & FULLY FUNCTIONAL  

---

## 1. Git Repository State

- **Branch:** `main`
- **Verified Commit SHA:** `f01a9be4460f207c72ffc55bd85c0dbc073cb95a`
- **Branch Parity:** Exact match across `HEAD`, `main`, `origin/main`, `develop`, and `origin/develop`.
- **Working Tree:** Clean (untracked scratch scripts isolated in `scratch/`).

---

## 2. Environment & Runtime Versions

| Tool / Runtime | Detected Version | Status |
| :--- | :--- | :--- |
| **Python** | 3.12.10 | Active (`backend/.venv`) |
| **Node.js** | v24.18.1 | Active |
| **npm** | 12.1.0 | Active |
| **PostgreSQL** | PostgreSQL 18 (Local Service PID 7428) | Active & Listening on port 5432 |
| **FastAPI / Uvicorn** | FastAPI 0.115+ / Uvicorn 0.30+ | Active Daemon PID 36744 |
| **Next.js** | Next.js 14.2.35 | Active Daemon PID 18116 |
| **Playwright / Chromium** | Playwright 1.65.0 (Chromium v1254) | Verified & Executed |

---

## 3. Active Services & URLs

All services were launched as background daemons and remain running on your local machine:

- **Frontend Application:** [`http://localhost:3000`](http://localhost:3000)
- **Backend API Base:** [`http://127.0.0.1:8000`](http://127.0.0.1:8000)
- **Backend Health Check:** [`http://127.0.0.1:8000/health`](http://127.0.0.1:8000/health) $\rightarrow$ `{"status":"ok","app":"SceneSteward","version":"v1"}`
- **Interactive Swagger API Documentation:** [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **Database Engine:** `postgresql+psycopg://...:5432/scenesteward` (Alembic Head `e1f2a3b4c5d6`)

---

## 4. Visual Inspection & Route Inventory

Live browser inspection was executed in Chromium across desktop (1440x900), tablet (768x1024), and mobile (375x667) viewports. Screenshots are preserved in `docs/screenshots/`:

| Route | Page Title / Purpose | Status | Visual Evidence |
| :--- | :--- | :--- | :--- |
| `/` | Landing page, platform ethics & entry | **PASS** | `01_landing_desktop_1440.png`<br>`01_landing_tablet_768.png`<br>`01_landing_mobile_375.png` |
| `/login` / Modal | Identity switching & authentication modal | **PASS** | `02_authenticated_session.png` |
| `/projects` | Documentary portfolio, search & metrics | **PASS** | `03_projects_portfolio_1440.png`<br>`03_projects_mobile_375.png`<br>`04_project_create_dialog.png`<br>`05_project_created_portfolio.png` |
| `/projects/[id]` | Production workspace (Roster, Intake, Review, Care, Audit) | **PASS** | `06_project_workspace_roster.png` |
| `/analytics` | Operational intelligence & export suite | **PASS** | `13_analytics_dashboard_1440.png`<br>`14_analytics_export_dialog.png`<br>`15_analytics_mobile_375.png`<br>`16_analytics_tablet_768.png` |
| `/participant/[id]` | Subject transparency portal (EN / HI) | **PASS** | `17_participant_portal_english.png` |

---

## 5. Playwright Automated Browser Test Suite Results

The full end-to-end Playwright test suite (`frontend/e2e/comprehensive_product_experience.spec.ts`) was executed against the live application:

| Test ID | Test Case | Status | Duration |
| :--- | :--- | :--- | :--- |
| **Test A** | Authentication flow, quick preset login, and session persistence | **PASS** | 5.2s |
| **Test B** | Navigation links, active state indicators, and mobile drawer | **PASS** | 8.1s |
| **Test C** | Projects workspace, real-time search filtering, and navigation | **PASS** | 715ms |
| **Test D** | Participant roster, language selection, and portal token link | **PASS** | 904ms |
| **Test E** | Canonical 15 categories, non-transitive invariants, and choice badges | **PASS** | 697ms |
| **Test F** | Advisory disclaimer banner and mandatory human decision rationale | **PASS** | 2.3s |
| **Test G** | Formal withdrawal warning banner and submission interface | **PASS** | 650ms |
| **Test H** | Analytics dashboard, KPI cards, category breakdown, and export dialog | **PASS** | 1.7s |
| **Test I** | Switching between preset personas refreshes header identity in real time | **PASS** | 1.4s |
| **Test J** | Responsive rendering across Mobile (375px), Tablet (768px), and Desktop (1440px) | **PASS** | 2.9s |
| **Test K** | Handles non-existent routes and records gracefully (404/422 fallbacks) | **PASS** | 616ms |

**Summary: 11 / 11 PASSED (100% in 34.6s)**

---

## 6. Functional Workflows Completed Live

### Workflow A: Production Coordinator Authentication & Project Creation
1. **Authenticated** via header persona preset: `"Olivia (Director / Owner)"` (`olivia@example.com`).
2. **Created Documentary Workspace** via UI modal:
   - **Title:** `"Arctic Voices (Demo Production)"`
   - **Description:** `"A longitudinal documentary chronicling Arctic wilderness researchers."`
3. **Persisted** directly into PostgreSQL; verified toast announcement and project card in `/projects`.

### Workflow B: Documentary Workspace & Participant Registration
1. Opened `/projects/[id]` workspace.
2. Verified all 5 primary tabs: **Roster**, **Intake**, **Review**, **Care**, and **Audit**.
3. Registered participant: `"Dr. Astrid Lindholm (fictional)"` with language `"English"`.
4. Verified that participant was saved to the PostgreSQL database under the active project.

### Workflow C: Operational Intelligence & Export Suite
1. Navigated to `/analytics`.
2. Verified live aggregation across:
   - Total Consents & Discussion Coverage KPIs.
   - 15 Canonical Consent Category distribution chart.
   - Advisory Agent operational metrics and non-authoritative disclaimer.
3. Opened **Export Report** dialog, verified format selection (CSV, JSON), and tested keyboard `Escape` dismissal.

### Workflow D: Ethical Invariant Enforcement
1. Verified AI extraction proposal accompanied by mandatory advisory banner:
   > *"AI extraction proposals are advisory and non-binding until human review is complete."*
2. Verified human review approval button remains disabled until non-empty rationale is supplied.
3. Verified fail-closed communication delivery returns HTTP 503 rather than false positive "Sent" when external SMTP/SMS provider is offline.

---

## 7. Responsive Viewport Verification

All responsive layout adaptations were confirmed in Chromium:
- **320px – 375px (Mobile):** Navigation collapses to accessible hamburger drawer; single-column card grids; touch-friendly tap targets ($\ge 44\times 44\text{px}$).
- **768px (Tablet):** Two-column card layouts; horizontally scrollable tables; breadcrumbs and sticky headers maintain alignment.
- **1024px – 1440px (Desktop):** Full multi-column dashboard with sticky sidebar and side-by-side review panes.

---

## 8. Console & Log Review

- **Browser Developer Console:**
  - Zero uncaught exceptions.
  - Zero React hydration errors.
  - One expected `422 Unprocessable Entity` on `/participant/demo-portal` (FastAPI correctly rejects non-UUID strings on UUID path parameters).
- **Backend FastAPI Logs:**
  - Clean startup and routing.
  - All database queries executed through SQLAlchemy with transactional integrity.
  - Zero unhandled 500 Internal Server Errors.

---

## 9. Current Operational Status

The application is **RUNNING LOCALLY RIGHT NOW**. You can immediately open your browser to explore it:

1. **Frontend:** [http://localhost:3000](http://localhost:3000)
2. **Backend API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
3. **To Log In as Demo Director:** Click **"Olivia (Director)"** in the top right header navigation.
4. **To Switch Personas:** Click **"Custom / Switch"** in the header to switch to Claire (Care Lead), Marcus (Producer), or Elena (Legal Counsel).

