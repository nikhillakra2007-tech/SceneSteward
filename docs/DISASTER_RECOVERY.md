# SceneSteward — Disaster Recovery & Business Continuity Plan

**Document Version:** 1.0.0  
**Status:** Active / Production Ready  
**Date:** 2026-11-04  

---

## 1. Objectives & Metrics

| Metric | Target | Verification Method |
|---|---|---|
| **Recovery Point Objective (RPO)** | < 1 hour (daily/hourly dumps) / < 5 min (WAL archive) | Backup schedule & replication lag metrics |
| **Recovery Time Objective (RTO)** | < 15 minutes | Automated restore script to new Postgres instance |
| **Data Integrity Guarantee** | Cryptographic proof (SHA-256 + TOC validation) | Automated post-backup verification |

---

## 2. Backup Architecture

SceneSteward uses PostgreSQL 18's native custom-format archive (`pg_dump -Fc`), providing transaction-consistent point-in-time snapshots with internal compression and metadata tables of contents.

### 2.1 Backup Execution
Backups are executed via `backend/scripts/backup_database.py`:
```bash
python -m scripts.backup_database --output-dir /var/backups/scenesteward
```

The script enforces:
1. **Transaction Consistency:** Backups run inside a single serializable transaction snapshot (`--format=custom`).
2. **Owner Isolation:** Omits hardcoded owners/privileges (`--no-owner --no-privileges`), allowing clean restoration into any target cluster or role topology.
3. **Automated Verification:** Immediately executes `pg_restore --list` against the generated dump to prove TOC integrity.
4. **Cryptographic Checksumming:** Computes SHA-256 digest and writes a companion `.meta.json` file.
5. **Level 9 Compression:** Minimizes network transfer and storage costs.

---

## 3. Restoration Procedure

### 3.1 Scenario A: Restoring to an Existing or New Database

1. **Verify Backup Integrity:**
   ```bash
   python -c "import hashlib; print(hashlib.sha256(open('backup.dump','rb').read()).hexdigest())"
   ```
   Confirm the output matches the digest in `backup.meta.json`.

2. **Initialize Roles (If restoring to a completely fresh PostgreSQL cluster):**
   ```bash
   psql -U postgres -d postgres -f backend/scripts/db_roles.sql
   ```
   This ensures `scenesteward_app` (DML only, `NOBYPASSRLS`) and `scenesteward_readonly` exist with correct passwords.

3. **Execute Automated Restore:**
   ```bash
   python -m scripts.restore_database --backup-file backend/var/backups/scenesteward_YYYYMMDD_HHMMSSZ.dump --target-db scenesteward
   ```
   `pg_restore` uses `--clean --if-exists --no-owner --no-privileges` to rebuild schema objects, tables, triggers, and data.

4. **Verify Schema & RLS State:**
   ```bash
   alembic -c alembic.ini check
   alembic -c alembic.ini current
   ```

5. **Verify Application Health:**
   ```bash
   curl -f http://127.0.0.1:8000/health/ready
   ```

---

## 4. Disaster Scenarios & Playbooks

### 4.1 Corrupt or Truncated Database
1. Immediately stop API workers to halt further mutations: `systemctl stop scenesteward` / `docker compose stop app`.
2. Provision a scratch database `scenesteward_recovery`.
3. Restore the latest verified dump into `scenesteward_recovery`.
4. Validate table row counts (`projects`, `participants`, `consent_records`, `audit_events`).
5. Point application `DATABASE_URL` to the recovered database and restart workers.

### 4.2 Cryptographic Key Compromise or Accidental Disclosure
1. If an active key (`APP_ENCRYPTION_KEY`) is suspected of exposure:
   - Generate a new 32-byte Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
   - Add new key to `APP_ENCRYPTION_KEYS` under new KID `prod_recovery_v1`.
   - Update `APP_ENCRYPTION_CURRENT_KID=prod_recovery_v1`.
2. Run online rotation without taking down the service:
   ```bash
   python -m scripts.rotate_encryption_keys --target-kid prod_recovery_v1
   ```
3. Remove the compromised key from `APP_ENCRYPTION_KEYS` and recycle secrets across environment stores.

---

## 5. Storage / Document Backup

Release documents and signed consent attachments stored in private buckets (`scenesteward-private` or local storage `/srv/scenesteward/backend/var/storage`) must be replicated out-of-band:
- **Cloud (Supabase/S3):** Enable Cross-Region Replication (CRR) and S3 Object Lock (WORM compliant) to prevent tampering or ransomware encryption.
- **Local/Self-Hosted:** Nightly `rsync -avz --delete` to an offsite secure storage server with append-only snapshots.

