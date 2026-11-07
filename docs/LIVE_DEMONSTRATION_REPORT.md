# SCENESTEWARD — LIVE DEMONSTRATION REPORT
**Document Reference:** `docs/LIVE_DEMONSTRATION_REPORT.md`  
**Execution Date:** 2026-11-06  
**Auditor:** Quality & Integration Engineering  
**Application State:** ACTIVELY RUNNING & LISTENING  

---

## 1. Actual Startup Commands

The application is running locally with the following exact commands:

### Backend FastAPI Server
```powershell
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
- **Listening Address:** `127.0.0.1:8000` (PID 32048)
- **Log Location:** `backend/var/logs/` or background daemon stdout.

### Frontend Next.js Server
```powershell
npm --prefix frontend start
```
- **Listening Address:** `http://localhost:3000` (PID 16964)
- **Built Chunks:** Standalone production build compiled from `frontend/src/app`.

### PostgreSQL Database
- **Service Name:** `postgresql-x64-18`
- **Listening Address:** `localhost:5432` (PID 7428)
- **Active Database:** `scenesteward` (Alembic Head: `e1f2a3b4c5d6`)

---

## 2. Local URLs & Health Endpoints

| Resource | URL | Expected Response | Verified Status |
| :--- | :--- | :--- | :--- |
| **Frontend Application** | `http://localhost:3000` | HTTP 200 (HTML Document) | **PASS** |
| **Projects Portfolio** | `http://localhost:3000/projects` | HTTP 200 (Projects Directory) | **PASS** |
| **Analytics Dashboard** | `http://localhost:3000/analytics` | HTTP 200 (Operational Intelligence) | **PASS** |
| **Backend Health Check** | `http://127.0.0.1:8000/health` | `{"status":"ok","app":"SceneSteward","version":"v1"}` | **PASS** |
| **Swagger Interactive Docs**| `http://127.0.0.1:8000/docs` | HTTP 200 (OpenAPI UI) | **PASS** |

---

## 3. Verified User Workflows

The following live workflows were executed and verified against the running application:

### Workflow 1: Production Coordinator Authentication & Project Creation
1. Authenticated via `POST /api/v1/auth/dev-token` as **Olivia Director** (`olivia@example.com`).
2. Sent `POST /api/v1/projects` with title `"Wilderness Echoes"`.
3. Verified HTTP 201 response with generated UUID `e646e4e6-f8ee-4228-920d-2e765002a40f`.
4. Queried PostgreSQL `projects` table directly and confirmed persistence.

### Workflow 2: Participant Registration & Portal Token Issuance
1. Registered subject `"Dr. Fiona Bennett (fictional)"` via `POST /api/v1/projects/{id}/participants`.
2. Verified record in PostgreSQL `participants` table.
3. Called `POST /api/v1/participants/{id}/access-token` to issue signed portal token.
4. Queried `/api/v1/participants/{id}/portal-access?token={token}` without staff session headers; confirmed subject record rendered under PostgreSQL Row Level Security (RLS).

### Workflow 3: Canonical Consent & Ethical Invariants
1. Recorded release form choices across all 15 canonical categories.
2. Granted `documentary_appearance`; left `promotional_clips` as `not_discussed`.
3. Created proposed use for `promotional_clips`.
4. Comparison engine flagged discrepancy: non-transitive invariant enforced (Appearance != Promotional).
5. Silence is never consent: Unrecorded category remained flagged as unapproved.

### Workflow 4: Advisory Review & Mandatory Human Decision Gate
1. Advisory agent analysis queued human review `e96c2292-25f6-41c6-a7b1-d71ce1e86ba3`.
2. Negative test: Attempted decision with empty reason; backend returned HTTP 422.
3. Positive test: Reviewer submitted decision `"needs_participant_discussion"` with mandatory written rationale.
4. Duplicate decision attempt returned HTTP 409 Conflict.

### Workflow 5: Participant Care & Fail-Closed Outbound Gate
1. Created communication draft regarding promotional footage consultation.
2. Negative test: Attempted send without approval; backend returned HTTP 412 Precondition Failed.
3. Director granted explicit approval.
4. Attempted send without configured SMTP provider; backend safely returned HTTP 503 Service Unavailable (fail-closed, no false positive "Sent" status).

### Workflow 6: Analytics & Audit Exports
1. Queried `/api/v1/analytics/overview?project_id={id}`.
2. Called `POST /api/v1/analytics/exports` with `format="json"`; verified structured payload.
3. Called `POST /api/v1/analytics/exports` with `format="csv"`; verified CSV headers and values.

---

## 4. Screenshot Index

Actual screenshots captured from Chromium browser rendering are preserved in `docs/screenshots/`:

| Screenshot File | Description | Viewport |
| :--- | :--- | :--- |
| `01_landing_desktop_1440.png` | Landing page hero and ethical principles | 1440x900 |
| `01_landing_tablet_768.png` | Responsive landing page on tablet | 768x1024 |
| `01_landing_mobile_375.png` | Mobile view of hero section | 375x667 |
| `02_mobile_navigation_drawer_375.png`| Mobile navigation drawer open | 375x667 |
| `03_authentication_modal.png` | Dev login & persona switcher modal | 1440x900 |
| `04_authenticated_director_header.png`| Active session with director badge | 1440x900 |
| `05_projects_portfolio_1440.png` | Projects portfolio directory | 1440x900 |
| `06_projects_portfolio_mobile_375.png`| Mobile project cards layout | 375x667 |
| `07_project_create_dialog.png` | Modal dialog for creating documentary | 1440x900 |
| `08_workspace_tab_roster.png` | Documentary workspace: Participant Roster | 1440x900 |
| `09_workspace_mobile_375.png` | Mobile workspace responsive view | 375x667 |
| `10_workspace_tab_intake.png` | Documentary workspace: Intake & Documents | 1440x900 |
| `11_workspace_tab_review_gate.png` | Documentary workspace: Human Review Gate | 1440x900 |
| `12_workspace_tab_care.png` | Documentary workspace: Participant Care | 1440x900 |
| `13_workspace_tab_audit_timeline.png`| Documentary workspace: Immutable Audit | 1440x900 |
| `14_analytics_dashboard_overview.png` | Analytics KPI cards & category charts | 1440x900 |
| `15_analytics_export_dialog.png` | Analytics export dialog (CSV/JSON) | 1440x900 |
| `17_participant_portal_english.png` | Subject transparency portal | 1440x900 |

---

## 5. Known Limitations

- **Email/SMS External Delivery:** Safely returns HTTP 503 when no third-party SMTP/Twilio credentials are configured in local environment.
- **OCR Pipeline:** PDF optical character recognition requires local `tesseract-ocr` and ClamAV daemon installation.
- **Persona Switcher:** The quick login presets are intended for development/staging environments only and are disabled in production mode (`APP_ENV=production`).

