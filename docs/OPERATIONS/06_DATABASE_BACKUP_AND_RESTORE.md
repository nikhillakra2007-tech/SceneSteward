# SceneSteward Runbook 06: Database Backup and Restore

**Document ID:** `RB-06-BACKUP-RESTORE`  
**Target Environment:** Staging, Production  
**Audience:** SREs, Database Administrators  
**Last Updated:** 2026-11-06  

---

## 1. Backup Architecture & Operational Invariants

SceneSteward database backup operations adhere to the following strict operational principles:

1. **Atomic Staging & Zero Partial Publication**:
   - Backups are written to a hidden staging path (`.tmp_bkp_<id>_<timestamp>.dump`).
   - If `pg_dump` fails or the integrity check fails, the temporary file is unlinked immediately.
   - The archive is published to its final filename only after passing verification.

2. **Concurrency Safety & Mutual Exclusion**:
   - Every backup invocation acquires a mutual exclusion file lock (`var/backups/.backup.lock`) via `fcntl` on POSIX systems or `msvcrt.locking` on Windows.
   - Concurrent backup jobs fail fast with exit code 1 to avoid resource thrashing and partial archive corruption.

3. **Cryptographic Integrity & Streaming Checksums**:
   - SHA-256 hashes are computed using a memory-bounded streaming generator (64 KB chunk size) during file generation.
   - Every backup produces a companion JSON manifest (`<archive_name>.meta.json`) containing cryptographic checksum, size, TOC count, timestamp, and duration.
   - Manifest files strictly redact all database passwords and credentials.

4. **Archive Readability Verification**:
   - Before publishing, `pg_restore --list` is executed against the staged dump to verify the Table of Contents (TOC). Archives with fewer than 5 TOC entries are rejected.

5. **Field-Level Encryption & Off-Site Replication**:
   - Backups support optional Fernet AES-128-CBC / HMAC-SHA256 encryption (`--encrypt-backup` / `--encryption-key`), producing `.dump.enc` artifacts.
   - Off-site mirror replication (`--offsite-dir`) copies both the archive and the manifest, verifying the replica's SHA-256 checksum before marking the backup successful.

---

## 2. Taking an On-Demand Backup

### Standard Backup Command
```bash
python scripts/backup_database.py --output-dir var/backups
```

### Encrypted Backup with Off-Site Mirroring
```bash
python scripts/backup_database.py \
  --output-dir var/backups \
  --encrypt-backup \
  --encryption-key "$APP_ENCRYPTION_KEY" \
  --offsite-dir /mnt/secure_offsite_vault
```

### Output Artifacts
- Archive: `var/backups/scenesteward_prod_YYYYMMDD_HHMMSSZ.dump` (or `.dump.enc`)
- Metadata Manifest: `var/backups/scenesteward_prod_YYYYMMDD_HHMMSSZ.meta.json`

### Metadata Manifest Specification
```json
{
  "backup_id": "bkp_a1b2c3d4e5f6_20261106_001500Z",
  "database": "scenesteward_prod",
  "created_at_utc": "2026-11-06T00:15:00.123456+00:00",
  "dump_file": "scenesteward_prod_20261106_001500Z.dump",
  "size_bytes": 143872,
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "toc_entries": 293,
  "encrypted": false,
  "duration_seconds": 1.24
}
```

---

## 3. Restoring from Backup

> [!WARNING]
> Restoring a database drops and recreates schema objects. Target databases in non-test environments or production require explicit confirmation tokens enforced by `lifecycle_guards.py`.

### Step 1: Pre-Restore Integrity Inspection
The restore utility automatically validates:
1. Manifest existence and JSON validity.
2. Archive streaming SHA-256 match against manifest.
3. Decryption (if archive is `.dump.enc`).
4. Readability via `pg_restore --list`.

To manually inspect TOC:
```bash
pg_restore --list var/backups/scenesteward_prod_YYYYMMDD_HHMMSSZ.dump
```

### Step 2: Executing Restore
For disaster recovery into target database `scenesteward_prod`:
```bash
python scripts/restore_database.py \
  --backup-file var/backups/scenesteward_prod_YYYYMMDD_HHMMSSZ.dump \
  --target-db scenesteward_prod \
  --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
```

For encrypted archives:
```bash
python scripts/restore_database.py \
  --backup-file var/backups/scenesteward_prod_YYYYMMDD_HHMMSSZ.dump.enc \
  --encryption-key "$APP_ENCRYPTION_KEY" \
  --target-db scenesteward_prod \
  --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
```

### Step 3: Exit Code Classification
- `0`: Complete success without warnings or errors.
- `1`: Non-fatal warnings (e.g. `--clean --if-exists` drops on nonexistent tables during cold restore).
- `2+`: Fatal restore failures; the utility raises `RuntimeError` and aborts.

### Step 4: Post-Restore Structural & Security Validation
Every restore automatically invokes `validate_restored_database()` which verifies:
- Minimum 20 core tables in schema `public`.
- Row-Level Security enabled on all sensitive tables (`relrowsecurity = true`).
- Minimum 60 RLS policies defined.
- Minimum 200 security and integrity triggers active.
- Alembic migration version matches expected schema head.
- Deterministic role provisioning (`scenesteward_app` and `scenesteward_readonly`) re-enforced.
- Cryptographic database trust handshake intact (`public.app_verify_trust_handshake`).

---

## 4. Automated Recovery Verification Exercises

To run the end-to-end disaster recovery exercise in an isolated sandbox:
```bash
APP_ENV=test python backend/scripts/verify_isolated_restore.py
```

To run the point-in-time recovery (PITR) exercise verifying temporal recovery precision:
```bash
APP_ENV=test python backend/scripts/verify_pitr_recovery.py
```
