# SceneSteward Database Architecture

## 1. Architectural Principles

The SceneSteward PostgreSQL database represents the single authoritative source of truth for the system.
Key invariants:
- **Zero implicit trust**: The application connects under `scenesteward_app` (`NOBYPASSRLS`), meaning every query is subject to Row Level Security.
- **Append-only audit log**: `audit_events` cannot be updated or deleted by the application user.
- **Declarative consent integrity**: Triggers prevent modifying confirmed consent records; superseded records are tracked chronologically.
- **Optimistic concurrency control**: Critical entities (`projects`, `participants`, `consent_records`, `proposed_uses`, `reviews`) include `version` counters checked on write.

---

## 2. Table Catalog by Logical Domain

The database schema consists of 20 tables:

### Identity & Access Control
- `users`: Core user accounts (email, display name, account status, avatar).
- `project_memberships`: Project-level user roles (`project_owner`, `producer`, `director`, `editor`, `participant_care_lead`, `viewer`, `participant`, `service_agent`) and status (`invited`, `active`, `suspended`, `removed`).

### Documentary Projects
- `projects`: High-level production units (title, logline, purpose, themes, intended audiences, project status).

### Participant Management
- `participants`: Subject records (display name, pronouns, preferred language, accessibility requirements, privacy preferences).
- `participant_contact_records`: Encrypted contact details (phone, email, postal address) protected by versioned symmetric key ring encryption.

### Release Documents & Text Extraction
- `release_documents`: Uploaded legal release forms, interview transcripts, and media files.
- `document_pages`: Extracted plain-text pages indexed by page number.

### Documentary Story & Narrative Elements
- `story_elements`: Narrative units, scenes, interview clips, and identifying details flagged with sensitivity levels.

### Consent & Decision Lifecycle
- `consent_records`: Versioned consent declarations (status: `draft`, `awaiting_confirmation`, `confirmed`, `superseded`, `revoked`).
- `consent_choices`: Granular category-specific agreements (`interview_recording`, `promotional_clips`, `voice_cloning`, etc.) with choices (`agreed`, `declined`, `not_discussed`, `needs_clarification`).

### Documentary Uses & Comparison Engine
- `proposed_uses`: New intended distributions, trailer cuts, and AI processing proposals.
- `proposed_use_analyses`: Comparative evaluations generated between proposed uses and confirmed consent.
- `reviews`: Pending human review requests linking proposed uses to required producer/care lead decisions.

### AI Agent Execution Records
- `agent_runs`: Audit records of agent invocations, prompt versions, models, execution times, and reasoning outputs.

### Participant Communications
- `participant_communications`: Outbound messages drafted for participants. Enforces human approval prior to dispatch.

### Task Management
- `tasks`: Action items for production team members (e.g., follow-up discussions, consent renewals).

### External Orchestration & Integration
- `integration_events`: Transactional outbox storing events awaiting external delivery (e.g. to Switch).
- `switch_room_links`: Mapping between SceneSteward projects/elements and Switch discussion rooms.

### Audit & System Metadata
- `audit_events`: Tamper-evident append-only ledger recording all actor actions, previous states, and new states.
- `alembic_version`: Tracks migration revision state.

---

## 3. Database Triggers & Invariants

PostgreSQL enforces critical domain rules via triggers:
1. `trg_prevent_confirmed_consent_update`: Prevents any UPDATE to a `consent_records` row once `record_status = 'confirmed'`.
2. `trg_consent_supersession`: Automatically marks older confirmed consent records as `superseded` when a new version is confirmed for the same participant.
3. `trg_prevent_audit_tampering`: Rejects UPDATE and DELETE operations on `audit_events` to preserve the accountability ledger.
4. `trg_enforce_communication_approval`: Rejects updating `participant_communications.communication_status` to `sent` unless `approved_by IS NOT NULL`.

---

## 4. Row Level Security (RLS) Implementation

All 18 application tables scoped to projects have RLS enabled and forced:
```sql
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
```

### Security Helper Functions
1. `app_current_user_id()`: Returns `current_setting('app.user_id', true)::uuid`. Returns NULL if unset.
2. `app_is_system()`: Returns TRUE when `current_setting('app.is_system', true) = 'true'`.
3. `app_authenticated()`: Returns TRUE when `app_current_user_id() IS NOT NULL`.
4. `app_has_project_role(p_project_id, VARIADIC p_roles)`: Evaluates whether `app.user_id` has an active membership in `p_project_id` matching any of the specified roles.

### Policy Structure
- **SELECT**: Restricted to users with active memberships in the owning project (or matching `created_by` on uncommitted project creations).
- **INSERT**: Allowed for authenticated users with appropriate project write roles.
- **UPDATE**: Restricted to specific roles with optimistic concurrency checks.
- **DELETE**: Restricted to project owners or disallowed entirely for audited entities.
- **Audit Ledger**: INSERT allowed for authenticated users and system context; UPDATE and DELETE completely denied.

