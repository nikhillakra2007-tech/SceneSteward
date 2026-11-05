# SceneSteward Runbook 17: Storage Management & Lifecycle

**Document ID:** `RB-17-STORAGE-MANAGEMENT`  
**Target Environment:** Staging, Production  
**Audience:** Storage Administrators, Compliance Officers  

---

## 1. Storage Topology
- **Local Storage Provider (`STORAGE_PROVIDER=local`)**:
  - Root directory: `/srv/scenesteward/backend/var/storage` (mounted volume `scenesteward-prod-storage`).
  - Access control: Cryptographically signed HMAC download URLs with 5-minute expiration (`DOWNLOAD_URL_TTL_SECONDS=300`).
- **Supabase Storage Provider (`STORAGE_PROVIDER=supabase`)**:
  - Private bucket: `scenesteward-production-documents`.
  - Direct presigned S3 URLs issued to client for uploads and downloads.

---

## 2. File Invariant & Security Policies
- **Upload Size Limit**: Strictly enforced at 25 MiB (`MAX_UPLOAD_BYTES=26214400`).
- **Decompression Bomb Protection**: Zip/Docx archives are inspected prior to extraction; decompression ratio capped at 100x and uncompressed bytes capped at 50 MiB.
- **Path Traversal Protection**: Upload keys are sanitized; path traversal (`../`) is rejected.
- **Antivirus Scanning**: Files are scanned via ClamAV before acceptance.

---

## 3. Orphaned File Pruning
To identify storage files without matching agreement records in PostgreSQL:
```bash
python -m scripts.prune_storage --dry-run
```
To purge orphaned temporary files older than 7 days:
```bash
python -m scripts.prune_storage --older-than-days 7 --confirm
```
