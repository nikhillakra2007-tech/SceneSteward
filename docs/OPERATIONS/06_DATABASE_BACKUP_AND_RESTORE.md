# SceneSteward Runbook 06: Database Backup and Restore

**Document ID:** `RB-06-BACKUP-RESTORE`  
**Target Environment:** Staging, Production  
**Audience:** SREs, Database Administrators  

---

## 1. Backup Strategy & Cadence
- **Type**: Compressed atomic custom format (`pg_dump -Fc -Z9`).
- **Cadence**: Full backup every 6 hours; pre-migration backups before every deployment.
- **Retention**: Keep last 28 days locally and mirrored to secure encrypted off-site object storage.
- **Integrity**: Every backup automatically verifies table of contents (`pg_restore -l`) and generates a companion `.meta.json` file with SHA-256 hash.

---

## 2. Taking an On-Demand Backup

Execute the backup script:
```bash
python -m scripts.backup_database --output-dir var/backups
```
*Output*:
- `var/backups/scenesteward_prod_YYYYMMDD_HHMMSSZ.dump`
- `var/backups/scenesteward_prod_YYYYMMDD_HHMMSSZ.meta.json`

Verify checksum:
```bash
sha256sum var/backups/*.dump
```

---

## 3. Restoring from Backup

> [!WARNING]
> Restoring a database replaces tables and data. Production restoration requires explicit override tokens enforced by `lifecycle_guards.py`.

### Step 1: Pre-Restore Verification
Verify the backup archive is intact:
```bash
pg_restore --list var/backups/scenesteward_prod_20261105_120000Z.dump
```

### Step 2: Execute Restore
For disaster recovery into target database `scenesteward_prod`:
```bash
python -m scripts.restore_database \
  --backup-file var/backups/scenesteward_prod_20261105_120000Z.dump \
  --target-db scenesteward_prod \
  --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
```

### Step 3: Verify Role Permissions
The restore script automatically re-applies runtime grants to `scenesteward_app` and `scenesteward_readonly`. Confirm via `psql`:
```sql
SELECT grantee, table_name, privilege_type 
FROM information_schema.role_table_grants 
WHERE grantee = 'scenesteward_app';
```

---

## 4. Automated Recovery Verification
To test disaster recovery without risking any existing database, run:
```bash
APP_ENV=test python backend/scripts/verify_isolated_restore.py
```
This provisions a disposable database, performs an atomic dump, restores it, validates all 20 tables, 69 RLS policies, 212 triggers, contact encryption roundtrips, and drops the disposable database.
