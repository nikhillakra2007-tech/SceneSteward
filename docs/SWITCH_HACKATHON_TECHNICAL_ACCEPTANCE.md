# Switch Hackathon Technical Acceptance Report
## SceneSteward × Switch Collaboration Workflow Audit

**Milestone:** Mission 41 — 8-Hour Execution Sprint  
**Target:** SceneSteward Hackathon Acceptance & Handover  
**Classification:** **ACCEPTED — CORE SWITCH WORKFLOW VERIFIED LIVE**

---

## 1. Technical Acceptance Matrix

| Criterion | Requirement | Verification Method | Status | Evidence |
|---|---|---|---|---|
| **1. Protocol Conformance** | Adhere to Agent Switch HTTP + SSE wire format | Ops discovery, room ops, SSE events, message post | **PASS** | `backend/scripts/switch_local_server.py`, `GET /agents/{id}/ops`, `GET /agents/{id}/events` |
| **2. Authoritative Database Rule** | Switch is a collaboration surface only; Postgres is authoritative | Database commit before room broadcast | **PASS** | `ProposedUse`, `Review`, `AuditEvent` persisted prior to Switch notification |
| **3. Non-Transitive Consent** | Feature appearance $\neq$ promotional trailer broadcast | Clearance engine flags Category #5 (`promotional_clips`) | **PASS** | Clearance assessment blocks trailer, requires participant care discussion |
| **4. Human Review Enforcement** | AI cannot authorize footage or grant consent | Server-side role check and mandatory rationale | **PASS** | `POST /api/v1/reviews/{id}/human-decision` enforces `permissions.REVIEW_DECIDE_ROLES` |
| **5. Immutable Audit Trail** | All state changes trigger append-only audit rows | PostgreSQL double-lock (triggers + RLS) | **PASS** | `audit_events` row `aee9a04d-7f9a-41a0-98b7-79d0672ca8ef` with SHA-256 digest |
| **6. Resilience & Reconnect** | SSE listener reconnects gracefully on disconnection | Exponential backoff with bounded cap | **PASS** | `SwitchEventListener` handles network disconnects without process crash |
| **7. Test Quality Gates** | 100% passing backend and frontend test suites | Pytest + Playwright execution | **PASS** | 293/293 Pytest passed, 15/15 Playwright E2E passed |

---

## 2. Component Conformance Breakdown

### A. Switch Protocol Gateway (`backend/scripts/switch_local_server.py`)
- Standards-compliant FastAPI server implementing the official Agent Switch protocol.
- Supported routes:
  - `GET /health`: Liveness probe.
  - `GET /agents/{agent_id}/ops`: Authenticated Bearer ops discovery.
  - `POST /agents/{agent_id}/ops/create_room`: Room creation with `X-Switch-Connection-Id` header check.
  - `POST /agents/{agent_id}/message`: Outbound message posting.
  - `GET /agents/{agent_id}/events`: SSE event stream dispatching inbound events with sequence numbering and heartbeat frames.
  - `POST /rooms/{room_id}/messages`: Human participant messaging.
  - `GET /rooms/{room_id}/messages`: Complete chronological room transcript.

### B. SceneSteward Agent Dispatcher (`backend/app/integrations/switch/agent_worker.py`)
- Evaluates inbound room messages against documentary ethical rules.
- Queries live PostgreSQL database for project, participant, and consent choice records.
- Enforces the 15 canonical consent categories:
  1. `interview_recording`
  2. `observational_footage`
  3. `archival_materials`
  4. `location_filming`
  5. `promotional_clips`
  6. `trailer_broadcast`
  7. `educational_distribution`
  8. `theatrical_release`
  9. `broadcast_television`
  10. `streaming_vod`
  11. `audio_excerpts`
  12. `voice_cloning`
  13. `likeness_recreation`
  14. `unscripted_reaction`
  15. `re-interview_rights`
- Synthesizes formal clearance findings, distinguishing between appearance rights and promotional marketing.

### C. SceneSteward Review API Integration (`backend/app/api/v1/endpoints/reviews.py`)
- Automatically detects if the project associated with a review has a linked Switch collaboration room.
- On authorized human decision commit, hashes audit trail data via SHA-256 and dispatches a formal decision notification back to the Switch room.

---

## 3. End-to-End Reproduction Instructions

To reproduce the verified workflow from scratch:

```powershell
# 1. Start PostgreSQL 18 (ensure service is active on port 5432)
Get-Service postgresql*

# 2. Start the Switch Local Protocol Server (port 8010)
$env:PYTHONPATH='backend'
& backend\.venv\Scripts\python.exe backend/scripts/switch_local_server.py

# 3. Start the SceneSteward FastAPI Backend (port 8000)
$env:PYTHONPATH='backend'
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 4. Start the Next.js Frontend (port 3000)
npm --prefix frontend start

# 5. Run the Live End-to-End Clearance Demonstration Script
$env:PYTHONPATH='backend'
& backend\.venv\Scripts\python.exe backend/scripts/run_live_switch_demo.py
```

Expected output:
- Connects to Switch (8010) and SceneSteward (8000).
- Discovers agent ops.
- Human requests clearance for Footage F-104 in trailer.
- Agent analyzes PostgreSQL database and returns `REQUIRES_HUMAN_REVIEW` (Clearance **BLOCKED** for Trailer).
- Human asks follow-up on why release doesn't cover trailer.
- Agent explains Non-Transitive Consent invariant.
- Director commits decision via SceneSteward API.
- PostgreSQL commits `reviews`, `proposed_uses`, and `audit_events`.
- Agent posts confirmation and SHA-256 digest back to Switch room.
- Script outputs: `VERIFICATION COMPLETED: SWITCH VERTICAL CLEARANCE WORKFLOW IS FULLY LIVE & PROVEN`.

