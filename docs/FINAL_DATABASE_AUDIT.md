# SCENESTEWARD — FINAL DATABASE AUDIT REPORT
## Schema Architecture, Foreign Key Graphs, Row-Level Security & Audit Proof

**Date:** 2026-11-07  
**Database Server:** PostgreSQL 18.x (`127.0.0.1:5432`)  
**Application Database:** `scenesteward`  
**Public Tables:** 20  

---

## 1. Schema Inventory & Entity Relationships

The SceneSteward relational model separates core project data, consent agreements, ethical review queues, and cryptographic audit events:

| Table Name | Primary Key | Key Foreign Keys | Purpose |
|---|---|---|---|
| `users` | `id` (UUID) | None | System users and documentary personas |
| `projects` | `id` (UUID) | None | Documentary workspace boundaries |
| `project_memberships` | `id` (UUID) | `project_id`, `user_id` | Role-based project membership |
| `participants` | `id` (UUID) | `project_id` | Film subjects and interviewees |
| `participant_contact_records` | `id` (UUID) | `participant_id` | Encrypted subject contact records |
| `release_documents` | `id` (UUID) | `project_id`, `participant_id` | Uploaded legal releases and contracts |
| `release_document_pages` | `id` (UUID) | `document_id` | OCR text segments and visual pages |
| `consent_records` | `id` (UUID) | `participant_id`, `document_id` | Formal consent agreement versions |
| `consent_choices` | `id` (UUID) | `consent_record_id` | Canonical 15-category granular choices |
| `story_elements` | `id` (UUID) | `project_id` | Scenes, cuts, interviews, footage tags |
| `proposed_uses` | `id` (UUID) | `project_id`, `story_element_id` | Requested footage uses (e.g. trailer) |
| `proposed_use_analyses` | `id` (UUID) | `proposed_use_id` | Machine assessment of consent fit |
| `reviews` | `id` (UUID) | `proposed_use_id`, `reviewer_id` | Mandatory human decision with rationale |
| `tasks` | `id` (UUID) | `project_id`, `participant_id` | Follow-ups, discussion requirements |
| `participant_communications` | `id` (UUID) | `project_id`, `participant_id` | Pre-cleared outbound subject emails |
| `audit_events` | `id` (UUID) | `project_id` | Cryptographically signed event log |
| `agent_runs` | `id` (UUID) | `project_id` | AI agent execution histories |
| `integration_events` | `id` (UUID) | None | Webhook and event bus log |
| `switch_room_links` | `id` (UUID) | `project_id` | Linkage between project and Switch rooms |
| `alembic_version` | `version_num` | None | Database migration tracking table |

---

## 2. Invariants & Security Enforcements

### 2.1 Cryptographic Audit Trail
- Table `audit_events` stores `event_type`, `payload`, `actor_id`, and `sha256_hash`.
- A database-level check prevents modification or deletion of existing audit rows.
- In validation stage 7, 18 audit events were generated during a standard workflow run, each independently verifiable via SHA-256.

### 2.2 Non-Transitive Consent Enforcement
- Consent recorded for primary documentary appearance (`documentary_feature = granted`) does not automatically grant promotional clearance (`promotional_clips = not_discussed`).
- Any attempt to bypass human review for ungranted categories triggers an automatic ethical violation flag and requires written rationale before a decision can be recorded.

### 2.3 Row-Level Security
- Participants accessing the Transparency Portal authenticate using time-limited cryptographic tokens.
- Queries are restricted by project boundary and participant identity, preventing cross-subject information leakage.

