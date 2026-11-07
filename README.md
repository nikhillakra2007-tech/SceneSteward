# SceneSteward

> **Participant-Centred Documentary Consent, Scope Verification & Production Workspace**

SceneSteward is a specialized backend and database platform designed for documentary film productions. It ensures that participant consent remains explicit, granular, versioned, and legally auditable across the entire documentary lifecycle—from initial release signature to promotional trailers and external distribution.

---

## 1. Problem Statement

In documentary and non-fiction media production, participant consent agreements are frequently treated as static, one-time paper waivers. In modern multi-platform distributions:
- Footage recorded for an intimate documentary interview is often repurposed for high-exposure promotional trailers, social media campaigns, or third-party AI voice reconstruction without explicit consent.
- Ambiguous waivers lead to ethical violations, breach of participant trust, and legal exposure for production houses.
- Production teams lack an automated, deterministic mechanism to verify whether a proposed creative use aligns with what a participant actually agreed to.

**SceneSteward solves this by enforcing a non-negotiable core principle:**
> *"A participant's agreement to one use must never automatically become agreement to another use. Silence is never agreement."*

---

## 2. Main Features

- **Granular, Versioned Consent Records**: Participants make explicit choices across 15 standard categories (e.g. `interview_recording`, `theatrical_documentary`, `promotional_clips`, `voice_cloning`, `synthetic_likeness`). New facts create new immutable versions; older versions are superseded.
- **Deterministic Scope Comparison Engine**: Compares proposed production uses against confirmed participant consent choices. Categorizes outcomes into `RECORDED_CHOICE_MATCH`, `NEEDS_DISCUSSION`, `PARTICIPANT_DECLINED`, or `HUMAN_REVIEW_REQUIRED`.
- **Advisory AI Multi-Agent Pipeline**: Specialized agents (`consent_analyst`, `story_change_analyst`, `participant_advocate`, `ethics_reviewer`, `production_coordinator`) analyze proposals and draft participant check-in communications. Agents operate advisory-only; they can never authorize use or alter consent records.
- **Human-in-the-Loop Review & Tasks**: Flags conflicts or missing categories as prioritized human review tasks for Participant Care Leads and Directors before distribution.
- **Cryptographic PII Protection**: Participant contact information is encrypted at rest using 256-bit Fernet encryption with zero-downtime key rotation support.
- **Fail-Closed Antivirus Scanning**: Integrated ClamAV inspection rejects infected or uninspected media uploads before permanent storage.
- **Multi-Tenant Row-Level Security (RLS)**: PostgreSQL 18 RLS policies enforce strict project boundaries using an HMAC-SHA256 authenticated database identity trust boundary.
- **Immutable Append-Only Audit Trail**: Full ledger of every proposal, comparison finding, human decision, and consent revision.
- **Asynchronous Outbox & Retry Worker**: Reliable event delivery to the Switch collaboration network with atomic lease recovery and dead-letter handling.

---

## 3. High-Level Architecture

```
+---------------------------------------------------------------------------------+
|                               CLIENT APPLICATIONS                               |
|                  (Web Dashboard / Mobile App / Switch Room Link)                |
+----------------------------------------+----------------------------------------+
                                         | HTTPS (Bearer JWT)
                                         v
+---------------------------------------------------------------------------------+
|                         SCENESTEWARD FASTAPI BACKEND                            |
|                                                                                 |
|  +-------------------+  +--------------------+  +----------------------------+  |
|  | Auth Dependencies |  | Consent Engine     |  | Advisory AI Agents         |  |
|  | (Supabase / Dev)  |  | (Deterministic)    |  | (Claude 3.5 Sonnet/Offline)|  |
|  +---------+---------+  +---------+----------+  +-------------+--------------+  |
|            |                      |                           |                 |
|            |                      | Security Context          |                 |
|            v                      v (app.current_user_id)     v                 |
|  +---------------------------------------------------------------------------+  |
|  |                 SQLAlchemy 2.0 ORM & Connection Pool                      |  |
|  +-------------------------------------+-------------------------------------+  |
+----------------------------------------|----------------------------------------+
                                         | TCP (HMAC Authenticated Sessions)
                                         v
+---------------------------------------------------------------------------------+
|                       POSTGRESQL 18 DATABASE LAYER                              |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  | private.app_secrets (HMAC identity validation & runtime verification)     |  |
|  +---------------------------------------------------------------------------+  |
|  | Row-Level Security (RLS) Policies on 18 Tables (Tenant Isolation)         |  |
|  +---------------------------------------------------------------------------+  |
|  | Append-Only Audit Events | Composite Integrity FKs | Triggers             |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
```

---

## 4. Technologies Used

- **Runtime & Web Framework**: Python 3.12, FastAPI, Uvicorn, Pydantic v2
- **Database & Migration Engine**: PostgreSQL 18, SQLAlchemy 2.0, Alembic, Psycopg 3
- **Security & Cryptography**: PostgreSQL Row-Level Security (RLS), HMAC-SHA256 Context Signing, Cryptography (Fernet 256-bit AES-CBC)
- **Malware Protection**: ClamAV Daemon (`zINSTREAM` socket wire protocol)
- **AI & Integrations**: Anthropic Claude 3.5 Sonnet API (with deterministic offline fallback), Supabase Auth & Storage SDKs, Switch Outbox Worker
- **Containerization**: Docker Engine 29+, Docker Compose v2, Alpine/Debian Slim Multi-Stage Images

---

## 5. Repository Structure

```text
SceneSteward/
├── README.md                          # Project documentation & operational runbook
├── .gitignore                         # Secret protection & artifact exclusion rules
├── .dockerignore                      # Minimal Docker build context configuration
├── docker-compose.staging.yml         # Multi-container staging stack definition
├── docker-compose.yml                 # Local development compose definition
│
├── backend/                           # Backend application root
│   ├── Dockerfile                     # Multi-stage non-root container specification
│   ├── pyproject.toml                 # Ruff, pytest, and project metadata
│   ├── requirements.txt               # Production dependencies
│   ├── requirements-dev.txt           # Test and linting dependencies
│   ├── alembic.ini                    # Alembic migration configuration
│   ├── .env.example                   # Safe development environment template
│   ├── .env.staging.example           # Safe staging environment template
│   │
│   ├── app/                           # Core application package
│   │   ├── api/                       # REST endpoints & dependency injection
│   │   ├── core/                      # Configuration, database engine, security
│   │   ├── models/                    # SQLAlchemy declarative models
│   │   ├── schemas/                   # Pydantic v2 validation schemas
│   │   ├── services/                  # Business logic (comparison, encryption, scanner)
│   │   ├── agents/                    # Multi-agent advisory pipeline
│   │   ├── workflows/                 # End-to-end documentary workflows
│   │   └── integrations/              # External adapters (Supabase, Switch, ClamAV)
│   │
│   ├── migrations/                    # Linear Alembic database migrations
│   │   └── versions/                  # Schema revisions (6589..., c7a1..., e1f2...)
│   │
│   ├── tests/                         # Automated test suite
│   │   ├── unit/                      # Encryption, comparison, and utility tests
│   │   ├── integration/               # API, auth, document, and worker tests
│   │   ├── security/                  # RLS tenant isolation & trust boundary tests
│   │   └── e2e/                       # Full 29-step documentary lifecycle tests
│   │
│   └── scripts/                       # Operational scripts
│       ├── switch_retry.py            # Outbox retry worker daemon
│       ├── run_container_workflow.py  # Synthetic container acceptance verification
│       ├── backup_database.py         # Snapshot backup utility
│       ├── restore_database.py        # Isolated restore verification utility
│       └── rotate_encryption_keys.py  # PII encryption key rotation utility
│
└── docs/                              # Comprehensive technical documentation & audits
```

---

## 6. Prerequisites

- **Python**: 3.12 or higher
- **PostgreSQL**: 15+ (PostgreSQL 18 recommended for production parity)
- **Docker**: Docker Desktop 29+ with WSL2 / Linux containers (for containerized stack)
- **Package Manager**: `pip` or `uv` (recommended for fast virtualenv creation)

---

## 7. Local Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/nikhillakra2007-tech/SceneSteward.git
cd SceneSteward
```

### 2. Set Up Virtual Environment
```bash
cd backend
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements-dev.txt
```

---

## 8. Environment Configuration

SceneSteward includes safe environment templates. Copy the development template:
```bash
cp .env.example .env
```

Configure the following essential variables in `backend/.env`:
```ini
APP_ENV=development
DATABASE_URL=postgresql+psycopg://scenesteward_app:APP_PASS@127.0.0.1:5432/scenesteward
DATABASE_IDENTITY_SECRET=CHANGE_ME_TO_RANDOM_HEX_32
APP_ENCRYPTION_KEY=CHANGE_ME_TO_FERNET_KEY
AUTH_PROVIDER=dev
AUTH_DEV_SECRET=CHANGE_ME_TO_RANDOM_HEX_32
```

> [!WARNING]
> Never commit `.env` or `.env.staging` files. Real secrets must remain strictly excluded from version control.

---

## 9. Database Setup & Migrations

### 1. Create Database Roles and Databases
Connect to PostgreSQL as a superuser (`postgres`):
```sql
CREATE ROLE scenesteward LOGIN PASSWORD 'OWNER_PASSWORD';
CREATE ROLE scenesteward_app LOGIN PASSWORD 'APP_PASSWORD' NOBYPASSRLS;

CREATE DATABASE scenesteward OWNER scenesteward;
CREATE DATABASE scenesteward_test OWNER scenesteward;
```

### 2. Run Alembic Migrations
Apply all linear migrations up to head (`e1f2a3b4c5d6`):
```bash
export ALEMBIC_DATABASE_URL="postgresql+psycopg://scenesteward:OWNER_PASSWORD@127.0.0.1:5432/scenesteward"
alembic -c alembic.ini upgrade head
```

---

## 10. How to Run the Backend

Start the FastAPI application with live reload:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger)**: `http://127.0.0.1:8000/docs`
- **OpenAPI JSON Specification**: `http://127.0.0.1:8000/openapi.json`
- **Health Check Endpoint**: `http://127.0.0.1:8000/health`

---

## 11. How to Run Tests

SceneSteward contains an automated test suite verifying unit logic, API endpoints, RLS security policies, and end-to-end documentary workflows.

Run all tests:
```bash
pytest tests -v
```

Run test categories individually:
```bash
# Unit tests (encryption, comparison engine)
pytest tests/unit -v

# Security tests (PostgreSQL RLS isolation, HMAC trust boundary)
pytest tests/security -v

# Integration tests (auth, documents, malware scanning)
pytest tests/integration -v

# End-to-end lifecycle test
pytest tests/e2e -v
```

Run Ruff linting and style checks:
```bash
ruff check .
```

---

## 12. How to Run the Docker Staging Environment

SceneSteward provides an isolated multi-container staging stack matching production architecture.

### 1. Build and Start the Staging Stack
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml up -d --build
```

### 2. Verify Container Health
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml ps
```

Expected output:
- `scenesteward-staging-api` (Port `8001 -> 8000`, `healthy`)
- `scenesteward-staging-db` (Port `5433 -> 5432`, PostgreSQL 18 Alpine, `healthy`)
- `scenesteward-staging-clamav` (Port `3310 -> 3310`, ClamAV Daemon, `healthy`)
- `scenesteward-staging-worker` (`healthy`, outbox sweep daemon)
- `scenesteward-staging-migrate` (`exited (0)`, one-off migration init task)

### 3. Run the In-Container Synthetic Acceptance Workflow
```bash
docker exec -e PYTHONPATH=/srv/scenesteward/backend scenesteward-staging-api python scripts/run_container_workflow.py
```

### 4. Teardown
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml down
```

---

## 13. Switch Agent Collaboration Integration

SceneSteward features native integration with the **Switch agent collaboration protocol**, enabling real-time human–AI clearance workflows:
- **Switch Protocol Gateway**: Implements the official Switch wire format (`GET /health`, `GET /agents/{id}/ops`, `POST /agents/{id}/message`, `GET /agents/{id}/events` SSE).
- **Consent-Aware Clearance Agent**: Listens in Switch rooms, queries PostgreSQL for participant releases, enforces the 15 canonical consent categories and Non-Transitive Consent invariants.
- **Human Authority Loop**: Formal decisions are committed by authorized directors via SceneSteward's authenticated API; immutable audit events with SHA-256 digest chains are recorded and notified back to Switch.

### Running the Live Switch Clearance Demonstration
```powershell
# 1. Start Switch Local Protocol Gateway (Port 8010)
$env:PYTHONPATH='backend'
& backend\.venv\Scripts\python.exe backend/scripts/switch_local_server.py

# 2. Start SceneSteward FastAPI Backend (Port 8000)
$env:PYTHONPATH='backend'
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 3. Execute the Live End-to-End Vertical Clearance Workflow
$env:PYTHONPATH='backend'
& backend\.venv\Scripts\python.exe backend/scripts/run_live_switch_demo.py
```

---

## 14. Current Integration Status

| Integration Adapter | Protocol / Technology | Current Status | Verification Evidence |
|:---|:---|:---:|:---|
| **Switch Integration** | Agent Switch HTTP + SSE Protocol | **VERIFIED LIVE** | Live 11-step clearance workflow proven (`run_live_switch_demo.py`) |
| **PostgreSQL 18** | Psycopg 3, RLS, HMAC Trust Boundary | **VERIFIED** | 20 tables, 18 RLS tables, 69 policies, snapshot backup/restore verified |
| **ClamAV Daemon** | TCP Socket Wire (`zINSTREAM`) | **VERIFIED** | Clean scan passed; EICAR test signature intercepted and quarantined |
| **Outbox Retry Worker** | Background Daemon (`switch_retry.py`) | **VERIFIED** | Atomic sweeping, lease acquisition, and dead-letter routing verified |
| **Anthropic Claude** | Anthropic Messages API | **ADAPTER READY** | Offline deterministic fallback active; requires live staging API key |
| **Supabase Auth** | Supabase JWT & JWKS Verification | **ADAPTER READY** | Dev mock verified; requires live staging project reference & JWKS |
| **Supabase Storage** | S3 / Supabase Private Document Bucket | **ADAPTER READY** | Local encrypted storage verified; requires live bucket credentials |

---

## 15. License & Ethical Notice

SceneSteward is intended for ethical documentary and creative media management. It is designed to empower participants and protect human dignity across storytelling platforms.
