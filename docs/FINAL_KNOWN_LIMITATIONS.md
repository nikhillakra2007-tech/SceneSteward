# SceneSteward — Final Known Limitations & Operational Considerations

**Date:** November 2026  
**Auditor:** Principal Software Architect & Reliability Engineer  
**Repository:** `nikhillakra2007-tech/SceneSteward`  

---

## 1. Architectural Boundaries & Intentional Design Constraints

The following behaviors are intentional system boundaries designed to protect participant dignity and security, rather than bugs:

1. **Silence is Never Agreement:**
   - Unanswered requests or unaddressed categories never auto-advance or assume affirmative consent. They remain in `UNRESOLVED`, `not_discussed`, or `needs_clarification`.
   - Human review with recorded written rationale is strictly required to confirm choices.

2. **Fail-Closed Communication Dispatch:**
   - If an external communications provider (e.g. Switch, Twilio, SendGrid) is unconfigured or unreachable, the messaging subsystem intentionally returns HTTP 503 instead of queuing messages blindly or reporting false delivery.

3. **Restricted Storage of Encrypted Contacts:**
   - Participant phone numbers and email addresses are encrypted via Fernet keys and are accessible only to project owners, producers, participant care leads, or the participants themselves.
   - Database administrators querying raw PostgreSQL see only ciphertext.

---

## 2. Operational Considerations

1. **OCR / Scanned Document Quality:**
   - The document extraction pipeline supports PDF, TXT, MD, and DOCX files. Scanned PDF documents without embedded OCR text layers require an external pre-OCR processing step prior to ingestion for optimal clause detection.

2. **Antivirus Scanning Latency:**
   - In production environments with `ANTIVIRUS_FAIL_CLOSED=true`, ClamAV container startup requires a 60–90 second warm-up window to download definition databases. Initial document upload attempts during this boot window will safely fail closed with HTTP 412.

3. **Key Rotation Lifecycle:**
   - Rotating `DATABASE_IDENTITY_SECRET` or `APP_ENCRYPTION_KEY` requires executing the dedicated administrative scripts (`rotate_encryption_keys.py`) during scheduled maintenance windows.
