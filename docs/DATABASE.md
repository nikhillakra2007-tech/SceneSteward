# SceneSteward — Database Design

PostgreSQL 15+ (developed/tested on 18). UUID primary keys (`gen_random_uuid()`).
All timestamps `timestamptz` (UTC). Optimistic locking via `version` columns on mutable
entities (PATCH requires `expected_version` → 409 on mismatch). Consent history is
append-only by trigger, not by convention.

## ER diagram

```
 users ──< project_memberships >── projects
   │                                  │  │
   │                      ┌───────────┘  │
   │                      ▼              ▼
   ├──> participants ◄────┘   story_elements
   │     │
   │     ├──< participant_contact_records   (Fernet-encrypted payload)
   │     ├──< release_documents ──< release_document_pages
   │     ├──< consent_records ──< consent_choices
   │     │        ▲ (unique participant_id + version_number)
   │     ├──< proposed_uses ─────┐
   │     │        │              ▼
   │     │        │      proposed_use_analyses (outcome + findings JSONB)
   │     │        ▼
   │     │      reviews (human | agent; decision on the row)
   │     ├──< participant_communications  (draft → approved → sent)
   │     │
   │     └──────┬───────────────┐
   ▼            ▼               ▼
 audit_events  tasks      switch_room_links
   ▲            ▲               │
   └── every state change       ▼
 integration_events        (project- or participant-scoped rooms)
```

## Tables (19 + alembic_version)

| Table | Purpose | Notable constraints / indexes |
|---|---|---|
| users | provider identity; no passwords | UNIQUE(auth_provider, provider_user_id); CHECK(account_status); INDEX(email) |
| projects | production | CHECK(title non-empty, ≤200 chars); INDEX(status) |
| project_memberships | 1 user ↔ N projects, role per project | UNIQUE(project_id, user_id); CHECK(role, membership_status); INDEX(user_id), INDEX(project_id, membership_status) |
| participants | roster per project | CHECK(display_name non-empty); INDEX(project_id), INDEX(project_id, status) |
| participant_contact_records | protected contact data | value stored Fernet-encrypted (`encrypted_contact_data`); INDEX(participant_id) |
| release_documents | signed releases (distinct from consent) | UNIQUE(storage_key); CHECK(file_size 1B..50MB, signature_status, extraction_status); INDEX(participant_id), (project_id), (extraction_status) |
| release_document_pages | extracted text with page refs | UNIQUE(document_id, page_number); INDEX(document_id) |
| consent_records | versioned consent snapshots | UNIQUE(participant_id, version_number); CHECK(record_status, participant_confirmation, source_type); INDEX(participant_id, record_status, version_number) |
| consent_choices | per-category choice | CHECK(choice, category non-empty, confidence 0..1); INDEX(consent_record_id), INDEX(category) |
| story_elements | identifiable moments | CHECK(sensitivity_level); INDEX(project_id), INDEX(project_id, sensitivity_level) |
| proposed_uses | what production wants | CHECK(status); INDEX(project_id, status), (participant_id), (story_element_id) |
| proposed_use_analyses | engine output (append-only) | CHECK(outcome, engine_version); INDEX(proposed_use_id) |
| reviews | human/agent review + decision | CHECK(reviewer_type, status, decision; decision ⇒ decided_by+decided_at); INDEX(project_id, review_status), (proposed_use_id), (reviewer_id) |
| agent_runs | AI invocation trace | CHECK(agent_name, execution_status); INDEX(project_id, agent_name), (proposed_use_id), (execution_status) |
| participant_communications | drafts (never auto-sent) | CHECK(status; **sent requires approved_by + sent_at**); INDEX(project_id, participant_id), (status) |
| audit_events | accountability timeline | append-only by trigger; INDEX(participant_id, timestamp), (project_id, timestamp), (entity_type, entity_id), (correlation_id) |
| integration_events | external idempotency | UNIQUE(integration_name, external_event_id); CHECK(processing_status, attempt_count ≥ 0); INDEX(processing_status, created_at), (correlation_id), (project_id) |
| tasks | human-owned work | CHECK(type, status, priority, actor_type); INDEX(project_id, status), (owner_user_id, status), (participant_id), (source_type, source_id) |
| switch_room_links | Switch room correlation | UNIQUE(switch_room_id); UNIQUE(project_id, participant_id, room_type) |

## Row Level Security & Database Roles

PostgreSQL Row Level Security (RLS) is enabled across all 18 project-scoped tables:
- **Runtime Role:** `scenesteward_app` (DML only, `NOBYPASSRLS`). The web application and background workers connect strictly under this identity.
- **Migration Role:** `scenesteward` (schema owner, `BYPASSRLS`). Used exclusively for running Alembic migrations.
- **Transaction-Local Identity:** Every transaction injects `app.user_id` or `app.system='on'` using `set_config(..., true)`. Connections without an active context see zero rows (deny by default).
- For complete policy details and threat modeling, see [docs/DATABASE_SECURITY.md](DATABASE_SECURITY.md).

## Consent versioning model

- `consent_records` are numbered per participant (1, 2, 3…). A record becomes
  `confirmed` only via `POST /consent-records/{id}/confirm` (human-only roles).
- Confirming version N transitions all other `confirmed` versions of that participant
  to `superseded` **in the same transaction**. There is never more than one
  usable confirmed record.
- **Immutability triggers (migration b3f9c21a7d44):**
  - `consent_records`: once `participant_confirmation='confirmed'`, updates may only
    change `record_status` → `superseded`. Everything else (including `confirmed_at`)
    is rejected. DELETE always rejected.
  - `consent_choices`: once the parent record is confirmed, only
    `confirmed_by`/`confirmed_at` bookkeeping may change. DELETE rejected.
  - `audit_events`: UPDATE/DELETE always rejected.
- The comparison engine reads **only** `record_status='confirmed' AND
  participant_confirmation='confirmed'`. Silence/absent category = not agreed.
- Extraction never produces confirmed records: extracted proposals land in
  `awaiting_confirmation` with `participant_confirmation='unconfirmed'` and
  per-choice `confidence_if_extracted` + `evidence_reference=page:N`.

## Deletion policy

Nothing is hard-deleted by the application: members are soft-removed
(`membership_status='removed'`), participants are soft-withdrawn
(`participant_status='withdrawn'`), projects are archived. Audit rows always survive.

## Rollback limitations (important)

Downgrading `b3f9c21a7d44` drops the integrity triggers — protection, not data.
Downgrading `65898c97090c` **drops all tables and data**. Alembic will happily do it;
never run `alembic downgrade` against a database you care about, and never against
production. Test rollbacks only on scratch databases (see TESTING.md). Recovery from
a bad production migration = restore from backup + forward-fix migration.

## Migrations

`alembic -c alembic.ini upgrade head` — three revisions:
1. `65898c97090c`: Initial core tables, constraints, foreign keys, and indexes.
2. `b3f9c21a7d44`: Immutability triggers on `consent_records`, `consent_choices`, and `audit_events`.
3. `c7a1e52b93f0`: Least-privilege roles (`scenesteward_app`, `scenesteward_readonly`), Row Level Security policies across all 18 project-scoped tables, helper security-definer functions (`app_is_member`, `app_has_role`), and `integration_events.project_id` foreign key.

Verified: clean upgrade on empty DB, downgrade to base, re-upgrade; foreign keys, unique + CHECK constraints, trigger enforcement, and RLS isolation are exercised by `tests/integration/test_migrations.py` and `tests/security/test_rls_isolation.py`.
