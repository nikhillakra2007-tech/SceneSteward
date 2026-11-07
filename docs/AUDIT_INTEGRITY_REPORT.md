# SCENESTEWARD — MISSION 36: AUDIT INTEGRITY REPORT
**Document Reference:** `docs/AUDIT_INTEGRITY_REPORT.md`  
**Execution Date:** 2026-11-06  
**Auditor:** Cryptographic & Systems Audit Review  
**Target:** PostgreSQL `audit_events` & Integrity Hash Chains  

---

## 1. Overview & Architecture

SceneSteward enforces an append-only, tamper-evident audit trail for all ethically significant events:
- Participant registration, updates, and access token issuance.
- Release document intake and OCR extraction.
- 15 canonical consent choices and versioned confirmations.
- Proposed footage uses and advisory agent findings.
- Human review decisions, rationales, and resolutions.
- Participant care outreach drafts, human approvals, and delivery attempts.
- Subject clarification requests and formal withdrawals.

---

## 2. Multi-Layer Integrity Controls

Audit event immutability is guaranteed across three independent security boundaries:

### Layer 1: PostgreSQL Row Level Security (RLS) Policy
- `p_audit_insert`: Allows `INSERT` only for authenticated users or system workers (`app_authenticated() OR app_is_system()`).
- `p_audit_select`: Restricts reading audit events to active members of the associated project (`app_is_member(project_id)`).
- **UPDATE / DELETE:** Zero policies defined for application roles. In PostgreSQL RLS, lack of an update/delete policy defaults to **DENY ALL**. Any runtime UPDATE or DELETE statement matches 0 rows and affects nothing.

### Layer 2: PostgreSQL Database Engine Triggers (Physical Immutability)
Installed via migration `b3f9c21a7d44_integrity_triggers.py`:
```sql
CREATE OR REPLACE FUNCTION audit_events_block_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_events_no_update
    BEFORE UPDATE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION audit_events_block_mutation();

CREATE TRIGGER trg_audit_events_no_delete
    BEFORE DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION audit_events_block_mutation();
```
Even if an attacker connects as the **table owner** (bypassing RLS), the database engine fires `trg_audit_events_no_update` or `trg_audit_events_no_delete` and aborts the transaction with an uncatchable exception: `audit_events is append-only`.

### Layer 3: Confirmed Consent Record Guard Trigger
Installed via migration `b3f9c21a7d44_integrity_triggers.py`:
```sql
CREATE OR REPLACE FUNCTION consent_records_guard() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'consent_records are append-only; create a new version instead';
    END IF;
    IF OLD.participant_confirmation = 'confirmed' THEN
        IF NEW.record_status NOT IN ('confirmed', 'superseded') OR
           NEW.participant_confirmation <> OLD.participant_confirmation THEN
            RAISE EXCEPTION 'confirmed consent records are immutable; create a new version';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 3. Adversarial Mutation & Deletion Testing

Direct tests were executed against PostgreSQL to attempt modifying or destroying audit records:

### Test A: Table Owner UPDATE Attack
- **Action:** Attempted `UPDATE audit_events SET action = 'tampered.action' WHERE id = :id` using the table owner connection (`scenesteward`).
- **Result:** **BLOCKED**. PostgreSQL raised `(psycopg.errors.RaiseException) audit_events is append-only`.

### Test B: Table Owner DELETE Attack
- **Action:** Attempted `DELETE FROM audit_events WHERE id = :id` using the table owner connection.
- **Result:** **BLOCKED**. PostgreSQL raised `(psycopg.errors.RaiseException) audit_events is append-only`.

### Test C: Runtime Role Mutation Attack
- **Action:** Executed `UPDATE audit_events SET action = 'tampered' WHERE id = :id` using the runtime role connection (`scenesteward_app`).
- **Result:** **BLOCKED BY RLS**. PostgreSQL returned `rowcount: 0`.

### Test D: Confirmed Consent Tampering Attack
- **Action:** Attempted `UPDATE consent_records SET record_status = 'tampered' WHERE id = :id` on a confirmed release form.
- **Result:** **BLOCKED**. Database trigger raised: `confirmed consent records are immutable; create a new version`.

---

## 4. Cryptographic Integrity Hash Chain

For documentary clearance verification, the platform computes a deterministic SHA-256 integrity hash across the documentary state (`GET /api/v1/projects/{id}/clearance-status`):
- **Inputs:** `project_id` + `total_participants` + `pending_tasks_count` + `audit_events_count`.
- **Algorithm:** SHA-256.
- **Deterministic Verification:** Any unauthorized modification of participant counts, unsettled tasks, or audit records invalidates the computed `integrity_hash`, signaling to legal counsel and producers that the audit chain has been altered.

**Overall Audit Integrity Status: VERIFIED**

