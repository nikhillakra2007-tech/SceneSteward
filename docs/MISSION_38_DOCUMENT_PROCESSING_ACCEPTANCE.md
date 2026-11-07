# SCENESTEWARD — MISSION 38: DOCUMENT PROCESSING & FILE SECURITY ACCEPTANCE
**Document Reference:** `docs/MISSION_38_DOCUMENT_PROCESSING_ACCEPTANCE.md`  
**Execution Timestamp:** 2026-11-06T16:45:00Z  
**Auditor / Release Lead:** Antigravity Engineering Systems  

---

## 1. Document Pipeline Architecture

SceneSteward handles sensitive release agreements, talent contracts, and archival forms through a secure, non-public ingestion pipeline:

```
Participant / Crew
       │
       │ 1. POST /participants/{id}/documents/upload-url (RBAC: Owner / Producer / Care Lead)
       ▼
FastAPI Gateway ───► Issues Signed Capability Token (Storage Key + Signed PUT URL)
       │
       │ 2. Direct PUT raw bytes to Storage
       ▼
Encrypted Storage (Local var/storage or Supabase S3)
       │
       │ 3. POST /participants/{id}/documents/complete-upload
       ▼
Antivirus Inspection (ClamAV daemon / Mock scanner)
       │
       │ 4. If clean: Trigger extraction & AI advisory analysis
       ▼
Document Intelligence & Adversarial Resistance Filter
       │
       ▼
Awaiting Human Review & Confirmation (Never auto-applied)
```

---

## 2. Ingestion & Signed Capability Verification

Verified via `backend/tests/integration/test_documents.py`:
- **Capability URL Generation**: Generates pre-signed upload URL without requiring persistent cloud credentials on the client.
- **Round-Trip Upload / Download**: Successfully uploaded binary PDF (`PDF_BYTES`), completed upload, verified metadata persistence, and retrieved via time-limited signed download URL.
- **MIME Allowlist Enforcement**:
  - Permitted: `application/pdf`, `text/plain`, `text/markdown`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
  - Rejected: Disallowed MIME types (e.g. `application/x-executable`, `application/javascript`, `image/svg+xml`) fail immediately with `HTTP 400 Bad Request` or `HTTP 422`.

---

## 3. Text Extraction Pipeline

Text extraction is handled by `app/services/extraction.py`:
- **PDF Documents**: Extracted via `pypdf.PdfReader` with page-by-page mapping and max page cap (`MAX_PAGES = 500`). Encrypted PDFs fail safely with `PreconditionFailed`.
- **Word Documents**: Extracted via `python-docx` with paragraph joining.
- **Markdown / Plain Text**: UTF-8 stream decoding with replacement for invalid codepoints.
- **Integrity Rule**: Extracted text is stored in `document_pages` with foreign keys and page numbers. It is marked as **untrusted data** and never converts directly into confirmed consent.

---

## 4. Adversarial Document Intelligence & Sanitization

The Document Intelligence engine (`app/services/document_intelligence.py`) defends against hostile release forms and prompt injection attempts embedded inside scanned documents:

### 4.1 Filtered Adversarial Patterns
- `SYSTEM_PROMPT_OVERRIDE`: RegEx pattern targeting `"ignore all previous directives / system instructions"`.
- `ROLE_IMPERSONATION`: RegEx targeting `"act as system admin / root / developer"`.
- `DELIMITER_INJECTION`: Traps `[SYSTEM]`, `<<SYS>>`, `<admin>`, `{"override": ...}`.
- `FORCED_CONSENT_DIRECTIVE`: Traps `"mark all categories consented / grant all permissions"`.
- `SMUGGLED_CHARACTERS`: Strips zero-width non-joiners (`\u200B`), byte-order marks (`\uFEFF`), and bi-directional overrides (`\u202A`–`\u202E`).

### 4.2 Category Mapping & Confidence Scoring
- Clause detection maps clauses against the **15 Canonical Categories** using structured keyword dictionaries.
- Generates confidence score ($0.0$ to $1.0$) based on stated keywords, negative qualifiers ("not agreed", "strictly prohibited"), and clause context.
- **Safety Invariant**: All findings are tagged `status: advisory_only`. Even high-confidence ($0.98$) extractions require human confirmation before affecting release status.

---

## 5. Malware Scanning Verification Status

- **Local Development State**: `PROVIDER-MOCKED`. Passes clean files; correctly detects simulated signatures.
- **Production Staging Script**: `backend/scripts/verify_staging_clamav.py`.
- **Execution Test**:
  ```text
  Antivirus Provider: mock
  ClamAV Host: 127.0.0.1:3310
  [RESULT] BLOCKED: ClamAV daemon is not reachable on 127.0.0.1:3310 (No connection could be made)
  ```
- **Operational Requirement for Production**: Deploy ClamAV container (`clamav/clamav:latest`) listening on port 3310 with daily virus definition updates enabled (`freshclam`).

Result: **VERIFIED IN-CODE; INFRASTRUCTURE DEPENDENCY DOCUMENTED**.

