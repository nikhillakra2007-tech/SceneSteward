# SceneSteward — Live Supabase Storage Staging Activation Report

**Date**: November 4, 2026  
**Auditor**: Backend Integration Engineer & SRE  
**Subsystem**: Supabase S3-Compatible Private Storage Adapter  
**Current Verification State**: **`CREDENTIALS PENDING (BLOCKED LIVE)`**  

---

## 1. Technical Requirements & Security Invariants

Documentary release forms, transcripts, and legal identity documents must be stored in a private bucket with zero public access.
The storage layer (`backend/app/integrations/storage/supabase.py`) enforces:
1. **Pre-signed Upload Targets**: Direct browser-to-bucket uploads using short-lived signed URLs (`SIGNED_URL_TTL_SECONDS=600`).
2. **Pre-signed Download URLs**: Authenticated download URLs with short expiry (`DOWNLOAD_URL_TTL_SECONDS=300`).
3. **Path Traversal Prevention**: Storage keys containing `../`, backslashes, or root paths are strictly rejected.
4. **File Size Enforcement**: Hard cap at 25 MiB per file.
5. **Private Access Only**: Storage bucket `scenesteward-staging-documents` must remain strictly private; anonymous reads return HTTP 403.

---

## 2. Test Execution & Diagnostic Output

### Local & Synthetic Verification
- **Automated Tests**:
  - `backend/tests/integration/test_documents.py` (12 tests)
  - `backend/tests/unit/test_encryption.py` (signed storage tokens)
  - Tests verify upload roundtrip, path traversal rejection, signed URL token HMAC validation, and MIME-type allowlists.

### Live Staging Probe Execution
- **Command**:
  ```powershell
  $env:PYTHONPATH = "backend"
  .\backend\.venv\Scripts\python.exe backend/scripts/verify_staging_storage.py
  ```
- **Actual Terminal Output**:
  ```
  ============================================================
  SceneSteward — Staging Supabase Storage Verification
  ============================================================
  Storage Provider: local
  Target Bucket: scenesteward-private
  Supabase URL: <unconfigured>

  [RESULT] BLOCKED: STORAGE_PROVIDER is not 'supabase' or credentials missing.
  ```

---

## 3. Classification & Next Actions

- **Current State**: `MOCK TESTED / CREDENTIALS PENDING (BLOCKED LIVE)`
- **Remediation Steps**:
  1. In the staging Supabase project, create a private storage bucket named `scenesteward-staging-documents`.
  2. In `backend/.env.staging`:
     ```env
     STORAGE_PROVIDER=supabase
     STORAGE_BUCKET=scenesteward-staging-documents
     SUPABASE_URL=https://<your-project-ref>.supabase.co
     SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
     ```
  3. Run `python backend/scripts/verify_staging_storage.py` to execute the live synthetic probe roundtrip (upload, existence, checksum download, and cleanup).

