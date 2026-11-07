# SCENESTEWARD — MISSION 38: COMMUNICATION PROVIDER ACCEPTANCE
**Document Reference:** `docs/MISSION_38_COMMUNICATION_ACCEPTANCE.md`  
**Execution Timestamp:** 2026-11-06T16:45:00Z  
**Auditor / Release Lead:** Antigravity Engineering Systems  

---

## 1. Ethical Communication Workflow

Participant care and communication in documentary filmmaking carries high ethical and legal risk. SceneSteward implements an immutable, fail-closed communication state machine:

```
Producer / Care Lead
        │
        │ 1. POST /projects/{id}/communications
        ▼
Draft Created (Status: draft, Subject, Body)
        │
        │ 2. Attempt POST /send  ───► BLOCKED: HTTP 412 Precondition Failed
        ▼
Human Approval Gate
        │
        │ 3. POST /communications/{id}/approve (Owner / Producer / Care Lead)
        ▼
Approved State (Status: approved, approved_by: user_id, approved_at: timestamp)
        │
        │ 4. POST /communications/{id}/send
        ▼
Outbound Dispatcher (SMTP / Twilio / Mock)
        ├── If provider unconfigured: HTTP 503 (Status REMAINS 'approved')
        └── If delivery succeeds: HTTP 200 (Status transitions to 'sent')
```

---

## 2. Invariant & Safety Enforcement Testing

Verified via `backend/tests/integration/test_communications.py` and `backend/scripts/verify_documentary_lifecycle.py`:

| Safety Invariant | Expected Behavior | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **No Unapproved Outreach** | Sending a draft communication without prior human approval must fail closed. | Returned `HTTP 412 Precondition Failed` with error code `approval_required`. | `PASS` |
| **Editor Approval Lockout** | Editors must not have permissions to approve outbound communications to subjects. | Returned `HTTP 403 Forbidden`. | `PASS` |
| **Fail-Closed Delivery** | If SMTP credentials or Twilio keys are unset, delivery must fail without marking message "sent". | Returned `HTTP 503 Service Unavailable` (`no_provider_configured`). Database status remained `approved`. | `PASS` |
| **Immutable Audit Log** | Every stage of communication must write an immutable audit trail entry. | Verified entries: `communication.draft_created`, `communication.approved`, `communication.send_attempted`. | `PASS` |
| **Contact Access Audit** | Viewing decrypted participant email or phone must log an audit record. | Logged `participant_contact.read` with `contact_count` and user identity. | `PASS` |

---

## 3. Contact Data Encryption at Rest

Participant emails, phone numbers, and emergency contacts are encrypted at rest in PostgreSQL (`participant_contacts` table) using Fernet AES-256-CBC with HMAC-SHA256 authenticated encryption:
- Encryption key configured via `APP_ENCRYPTION_KEY`.
- Unprivileged database dump inspection confirms that contact fields contain ciphertext tokens (`gAAAAA...`), not plaintext emails or phone numbers.
- Key rotation supported via `backend/scripts/rotate_encryption_keys.py`.

---

## 4. Operational Fallback: 1-Click Clipboard Routing

When running in local release candidate mode or during external provider outages:
- The SceneSteward UI recognizes the `HTTP 503 no_provider_configured` error.
- A "Copy Draft & Contacts to Clipboard" button provides coordinators with pre-formatted text to route manually via their secure email client.
- Prevents documentary operations from grinding to a halt while preserving exact audit trails.

Result: **VERIFIED**. Fail-closed architecture prevents false delivery confirmations.

