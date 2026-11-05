# SceneSteward — Final Database & RLS Architecture Report

**Date:** November 2026  
**Auditor:** Principal PostgreSQL Database Architect  
**Repository:** `nikhillakra2007-tech/SceneSteward`  

---

## 1. Database Schema & Entities

The database schema comprises **20 relational tables** managed by 4 sequential Alembic migrations:
- `users`: Authenticated platform users and system accounts.
- `projects`: Documentary workspaces.
- `project_memberships`: Role-based project memberships (`project_owner`, `producer`, `director`, `archivist`, `legal`, `participant`).
- `participants`: Registered documentary participants.
- `participant_contact_records`: Fernet-encrypted sensitive contact information.
- `consent_records`: Versioned consent records (immutable when confirmed).
- `consent_choices`: Granular choices evaluated across the 15 canonical categories.
- `release_documents`: Uploaded legal release forms and contracts.
- `document_pages`: Extracted and sanitized page text for indexing.
- `story_elements`: Narrative scenes, interviews, and archival items.
- `proposed_uses`: Planned footage and likeness distributions.
- `use_findings`: Analytical findings attached to proposed uses.
- `reviews`: Mandatory human review decision records.
- `tasks`: Operational work items and participant follow-up duties.
- `participant_communications`: Outbound communication drafts awaiting approval.
- `integration_events`: Idempotency tracking for external systems.
- `agent_runs`: Advisory AI agent execution history.
- `timeline_events`: Participant-facing accountability history.
- `switch_room_links`: Switch integration metadata.
- `audit_events`: Append-only, tamper-resistant system audit trail.

---

## 2. Row-Level Security (RLS) Posture

- **18 Tables Protected by RLS:** Every project-scoped table enforces strict RLS policies under PostgreSQL 18.
- **Runtime Role:** Application connects as `scenesteward_app` (`NOBYPASSRLS`).
- **Composite Integrity:** Foreign keys enforce `(project_id, participant_id)` composite constraints, guaranteeing database-level referential consistency and preventing cross-tenant injection.

---

## 3. Cryptographic Identity Trust Boundary

PostgreSQL enforces an HMAC-SHA256 session trigger:
```sql
CREATE OR REPLACE FUNCTION fn_enforce_identity_trust()
RETURNS trigger AS $$
BEGIN
  -- Rejects session parameter tampering unless HMAC signature matches secret
  IF NOT verify_hmac_signature(current_setting('app.user_id', true), current_setting('app.user_sig', true)) THEN
    RAISE EXCEPTION 'Cryptographic identity signature mismatch';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 4. Migration Status & Head Revision

The schema is synchronized with Alembic head revision `e1f2a3b4c5d6_identity_trust_boundary_and_composite_integrity`.
Zero migration drift or pending revisions exist.
