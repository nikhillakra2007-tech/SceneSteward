# SCENESTEWARD — DEVELOPER HANDOVER & SYSTEM ARCHITECTURE GUIDE

**Welcome to SceneSteward.**  
This guide is written for engineers cloning, configuring, running, testing, and extending SceneSteward. It explains the system's architectural invariants, database security model, local and production runtimes, and how to verify everything without guesswork.

---

## 1. What is SceneSteward?

SceneSteward is a documentary consent management platform designed for documentary filmmakers, production coordinators, legal counsel, and participants.

### Core Non-Negotiables & Ethical Invariants
1. **Silence is Never Consent:** If a participant does not explicitly discuss or sign a category, that category defaults to `not_discussed`. It can **never** be inferred or defaulted to approved.
2. **AI is Strictly Advisory:** Advisory AI agents (legal, ethical, cultural, licensing) provide suggestions only. An AI model can **never** approve, decline, or clear footage. Final authority rests solely with authorized human reviewers.
3. **Mandatory Human Rationale Gate:** Every human decision approving or declining a proposed footage use requires a non-empty written rationale recorded in the immutable audit trail.
4. **Non-Transitive Consent Categories:** Permission to appear in a documentary (`documentary_appearance`) does **never** automatically grant promotional teaser rights (`promotional_clips`), nor does it grant permission for synthetic voice cloning (`voice_cloning`) or avatar recreation (`synthetic_likeness`). Each of the 15 canonical categories is strictly independent.
5. **Fail-Closed Communication:** Outbound outreach to subjects cannot be sent without prior human approval. In environments without an active external communication gateway, the system safely returns HTTP 503 instead of recording a false "Sent" state.

---

## 2. Capability Completion Matrix

The distinction between locally verified application code and external infrastructure integrations is fundamental:

| Capability | What Constitutes Completion | SceneSteward Implementation Status | Production Requirement |
| :--- | :--- | :--- | :--- |
| **Consent Engine** | Backend-enforced independent category decisions | **VERIFIED (100% in-code)**. 15 canonical categories validated in PostgreSQL and FastAPI. | Complete. Zero external dependencies needed. |
| **Audit Immutability** | Append-only triggers and tampering detection | **VERIFIED (100% in-code)**. PostgreSQL triggers block `UPDATE` and `DELETE`. Clearance status calculates SHA-256 integrity hash. | In production, forward audit events to an external write-once log sink / SIEM. |
| **Database Isolation**| RLS-enforced cross-tenant boundary | **VERIFIED (100% in-code)**. Multi-tenant RLS active on 18 tables with HMAC session signatures. | Complete. Enforced natively by PostgreSQL. |
| **OAuth / Identity** | Actual external IdP authentication | **SPLIT**: Local development uses `/api/v1/auth/dev-token` (HS256). | Production requires `AUTH_PROVIDER=supabase` with real Supabase project JWKS URL. |
| **Document OCR** | Actual PDF/image text extraction | **SPLIT**: Local environment supports text extraction; binary PDF OCR uses fallback. | Production requires host/container installation of `tesseract-ocr` binaries. |
| **Malware Scan** | Actual virus scanning | **SPLIT**: Local development uses mock antivirus provider (`antivirus_provider=mock`). | Production requires live ClamAV daemon (`clamav:3310`) with `ANTIVIRUS_FAIL_CLOSED=True`. |
| **Outbound Email** | Real SMTP message submission | **SPLIT**: Local environment safely fails closed (HTTP 503 `no_provider_configured`). | Production requires valid `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD`. |
| **Outbound SMS** | Real SMS gateway submission | **SPLIT**: Safely fails closed (HTTP 503). UI provides 1-click clipboard copy fallback. | Production requires Twilio / external SMS provider credentials. |
| **Backup & PITR** | Database backup & restore validation | **VERIFIED**. Local script `backend/scripts/restore_database.py` validates dump/restore. | Production requires automated cron/wal-g to offsite S3 storage. |

---

## 3. High-Level Architecture Map

```
┌─────────────────────────────────────────────────────────────┐
│                      Next.js 14 Frontend                    │
│   (App Router, React 18, Tailwind CSS, Lucide-React, Toast) │
│           http://localhost:3000                             │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / Bearer JWT
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.12)            │
│   • Auth Dependency (Bearer JWT claims verification)         │
│   • RBAC Policy Gate (app.core.permissions)                 │
│   • Advisory AI Agent Pipeline (Advisory findings only)     │
│   • Clearance Evaluation Engine (15 canonical categories)   │
│           http://127.0.0.1:8000                             │
└──────────────────────────────┬──────────────────────────────┘
                               │ psycopg v3 / SQLAlchemy 2.0
                               │ (Session identity: app.user_id + HMAC signature)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 PostgreSQL 18 Database Engine               │
│   • Role: scenesteward_app (Non-owner, subject to RLS)      │
│   • Row Level Security (RLS) active on 18 multi-tenant tables│
│   • Triggers: trg_audit_events_no_update / no_delete        │
│   • Trigger: consent_records_guard (Confirmed immutability) │
│   • Private Schema: app_secrets (HMAC trust verification)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Local Quickstart for New Developers

### Prerequisites
- Python 3.12+
- Node.js v20+ or v24+
- PostgreSQL 16+ or 18 running locally on port 5432
- Git

### Step 1: Clone & Environment Setup
```powershell
git clone https://github.com/nikhillakra2007-tech/SceneSteward.git
cd SceneSteward

# Copy environment template
cp backend/.env.example backend/.env
```

### Step 2: Database Initialization & Migrations
Ensure PostgreSQL is running locally, then execute migrations using the migration owner role:
```powershell
& backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

### Step 3: Launch Services
In two separate terminals:

**Terminal 1 (Backend FastAPI):**
```powershell
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

**Terminal 2 (Frontend Next.js):**
```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

Open [**http://localhost:3000**](http://localhost:3000) in your browser.

---

## 5. Development Authentication & Persona Presets

When running with `AUTH_PROVIDER=dev`, four development persona presets are built into the UI header:

| Preset Name | Role | Email | Intended Testing Scope |
| :--- | :--- | :--- | :--- |
| **Olivia Director** | `project_owner` | `olivia@example.com` | Project initialization, team administration, full clearance |
| **Claire Care** | `participant_care_lead`| `claire@example.com` | Participant intake, care inquiries, consent discussions |
| **Marcus Producer** | `producer` | `marcus@example.com` | Operational review, budget, timeline, analytics export |
| **Elena Legal** | `legal_counsel` | `elena@example.com` | Clearance status inspection, legal advisory findings |

Clicking any preset button calls `POST /api/v1/auth/dev-token` to issue an authenticated session token.

---

## 6. How to Run the Test Suites

SceneSteward maintains a three-tier test suite:

### 1. Backend Automated Tests (293 Tests)
Runs unit, integration, and security tests against the local database:
```powershell
& backend\.venv\Scripts\python.exe -m pytest backend/tests
```

### 2. Documentary Lifecycle Verification (8 Stages)
Runs an end-to-end dry run through all 8 stages of documentary production:
```powershell
& backend\.venv\Scripts\python.exe backend/scripts/verify_documentary_lifecycle.py
```

### 3. Playwright Browser E2E Tests (11 Tests)
Runs automated Chromium browser tests verifying UI responsiveness, modals, and workflows:
```powershell
$env:NODE_PATH = "C:\Users\nikhi\AppData\Local\npm-cache\_npx\420ff84f11983ee5\node_modules"
npx @playwright/test test frontend/e2e/comprehensive_product_experience.spec.ts
```

### 4. Static Analysis & Linting
```powershell
& backend\.venv\Scripts\python.exe -m ruff check backend
npm --prefix frontend run lint
```

---

## 7. How to Extend SceneSteward

### Adding a New API Endpoint
1. Define the Pydantic schema in `backend/app/schemas/`.
2. Implement route logic in `backend/app/api/v1/endpoints/`.
3. Require `CurrentUser` dependency; verify permissions with `app.core.permissions.can(user_role, "action")`.
4. Register the route in `backend/app/api/v1/router.py`.

### Adding a New Database Migration with RLS
1. Create migration:
   ```powershell
   alembic -c backend/alembic.ini revision -m "add_new_feature_table"
   ```
2. Enable Row Level Security in the migration script:
   ```sql
   ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;
   CREATE POLICY p_my_table_select ON my_table FOR SELECT TO scenesteward_app USING (app_is_member(project_id) OR app_is_system());
   ```
3. Apply migration:
   ```powershell
   alembic -c backend/alembic.ini upgrade head
   ```

### Adding a New Frontend Component or Page
1. Follow the Tailwind palette defined in `docs/FRONTEND/FRONTEND_DESIGN_SYSTEM.md`.
2. Never use `alert()` or `confirm()`; use the `useToast()` hook from `@/components/Toast`.
3. For modal dialogs, ensure `role="dialog"`, `aria-modal="true"`, and keyboard `Escape` dismissal handlers are implemented.

