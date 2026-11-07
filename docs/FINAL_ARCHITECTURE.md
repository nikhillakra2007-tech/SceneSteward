# SCENESTEWARD — FINAL ARCHITECTURE SPECIFICATION
## System Topologies, Service Boundaries, and Switch Collaboration Fabric

**Project:** SceneSteward  
**Milestone:** Final Master Engineering Completion  
**Target:** WeMakeDevs — Flip The Switch 2026 (Best Business Workflow Track)  

---

## 1. Architectural Blueprint

SceneSteward establishes an end-to-end human-in-the-loop ethical clearance platform for documentary productions, leveraging Switch for multi-agent and human collaboration.

```mermaid
sequenceDiagram
    autonumber
    actor Producer as Human Producer (Olivia Director)
    participant SwitchUI as Switch Platform / Team Room
    participant SwitchCore as Switch Core (Port 64432)
    participant Bridge as SceneSteward Switch Bridge
    participant SS_API as SceneSteward Backend (Port 8000)
    participant DB as PostgreSQL (Port 5432)

    Producer->>SwitchUI: "Check clearance for interview footage in promotional trailer"
    SwitchUI->>SwitchCore: Dispatch room message (Room ID: aeec10b9-...)
    SwitchCore->>Bridge: Deliver event via REST / SSE poll
    Bridge->>SS_API: Query Proposed Use & Consent Matrix for Dr. Fiona Bennett
    SS_API->>DB: Query 15 canonical consent categories & non-transitive invariants
    DB-->>SS_API: Primary interview signed; promotional clips = not_discussed
    SS_API-->>Bridge: Ethical analysis: Non-transitive violation flagged; requires human review
    Bridge->>SwitchCore: Post advisory assessment to Room
    SwitchCore->>SwitchUI: "Advisory: Promotional use is NOT covered by primary interview release."
    Producer->>SwitchUI: Provide human decision rationale: "Hold trailer release pending subject discussion"
    SwitchUI->>Bridge: Human feedback received
    Bridge->>SS_API: Commit formal review decision with required rationale
    SS_API->>DB: Store decision in 'reviews' & append-only cryptographic event in 'audit_events'
    SS_API-->>Bridge: Decision recorded with immutable hash
    Bridge->>SwitchCore: Notify room of committed human decision & audit confirmation
    SwitchCore->>SwitchUI: "Clearance Hold committed. Audit trail logged."
```

---

## 2. Component Specifications

### 2.1 Backend Layer (`/backend`)
- **App Entry:** `backend/app/main.py`
- **FastAPI Framework:** Implements strict CORS, rate limiting, request validation, and OpenAPI documentation.
- **Data Models:** Declarative SQLAlchemy models mapped to PostgreSQL 18.
- **Consent Category Matrix:** 15 canonical dimensions (including `promotional_clips`, `social_media`, `archival_syndication`, `ai_training_exclusion`).
- **Ethical Invariant Guards:** Non-transitive consent logic ensures capturing consent for primary footage does not transitively authorize promotional derivative uses.

### 2.2 Switch Collaboration Layer (`/backend/app/integrations`)
- **Switch Core Adapter:** `backend/app/integrations/antigravity/actual_switch_bridge.py`
  - Real-time connection to genuine local Switch Core (`127.0.0.1:64432`).
  - Agent registration via Switch Core `POST /agents` with bearer token validation.
  - Active room moderation (`POST /agents/{agent_id}/moderation/rooms`).
  - Bi-directional message routing (`POST /agents/{agent_id}/message` and `GET /agents/{agent_id}/events`).
- **Legacy Compatibility Layer:** Supports local switch simulator mode on port `8010` as a fallback development harness.

### 2.3 Persistence Layer (`PostgreSQL`)
- **Production Database:** PostgreSQL on default port `5432` (`scenesteward` database).
- **Audit Immutability:** Dedicated PostgreSQL trigger on `audit_events` verifying SHA-256 payload checksums.
- **Row-Level Security (RLS):** Project and tenant isolation enforcing that unauthorized users cannot view external documentary records.

### 2.4 Frontend Presentation Layer (`/frontend`)
- **Framework:** Next.js 14 App Router, React 18, Tailwind CSS.
- **Key Modules:**
  - `/projects`: Documentary workspace and production overview.
  - `/participants`: Subject rosters, contact tracking, language preferences.
  - `/consent`: 15-category matrix breakdown with status indicators.
  - `/reviews`: Advisory alerts with mandatory human decision inputs.
  - `/transparency`: Participant self-service portal with localized language switching.
  - `/analytics`: Real-time compliance metrics, CSV/JSON export dialogs.

