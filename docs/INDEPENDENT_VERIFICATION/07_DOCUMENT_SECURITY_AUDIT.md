# 07. Document Security & Storage Audit

## Executive Summary
This audit validates the document intake pipeline, anti-malware verification (ClamAV), decompression bomb protection, file type whitelisting, and presigned URL access controls.

## Security Controls Evaluated
1. **ClamAV Anti-Malware Scanning**:
   - Every uploaded document (PDF, PNG, JPG, TIFF) is dispatched to ClamAV scanning daemon before ingestion.
   - **Fail-Closed**: If ClamAV daemon is unreachable, the upload is rejected with HTTP 503 rather than processed blindly.
   - EICAR test signature detection: Upload immediately terminated with HTTP 422 `MALICIOUS_PAYLOAD_DETECTED`.
2. **Decompression Bomb Protection**:
   - Zip/gzip/PDF compressed streams are inspected for uncompressed ratio limits (max 10:1 ratio or 50 MB total decompressed size).
   - High-entropy nested streams are rejected before processing.
3. **MIME & Magic Byte Verification**:
   - File extensions are not trusted. Magic bytes (`%PDF-`, `\x89PNG`, `\xFF\xD8\xFF`) are verified via `filetype`/`python-magic`.
4. **Presigned URL Expiry**:
   - Document downloads use HMAC-signed temporary URLs expiring in 900 seconds (15 minutes).
   - Direct S3/MinIO bucket access is prohibited from outside the VPC.

## Automated Verification Results
- **Unit & Security Tests**:
  - `backend/tests/unit/test_clamav_scanner.py`: 8 passed.
  - `backend/tests/unit/test_document_upload_security.py`: 10 passed.
  - Fail-closed offline daemon handling verified.

## Conclusion
Document intake is robust against malicious uploads, file spoofing, decompression bombs, and unauthorized access. Gate status: **PASS**.
