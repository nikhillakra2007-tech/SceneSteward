# SceneSteward Runbook 07: Point-in-Time Recovery (PITR)

**Document ID:** `RB-07-PITR`  
**Target Environment:** Production  
**Audience:** Principal Database Administrators  

---

## 1. Principles & Objectives
Point-in-Time Recovery (PITR) allows restoring the database state to an exact millisecond prior to an incident (e.g., accidental deletion or malicious corruption).
- **Target RPO**: < 15 minutes.
- **Mechanism**: Base pg_dump backup + continuous PostgreSQL Write-Ahead Log (WAL) archiving.

---

## 2. PostgreSQL WAL Archiving Configuration
In `postgresql.conf` on the production database server:
```ini
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f'
archive_timeout = 900  # 15 minutes maximum lag between forced WAL switches
```

---

## 3. Recovery Procedure to Specific Timestamp

### Step 1: Stop All Ingress Traffic
Prevent new writes while restoring:
```bash
docker compose -f docker-compose.prod.yml stop api worker
```

### Step 2: Identify Recovery Target Time
Establish the exact timestamp (UTC) prior to the incident:
`recovery_target_time = '2026-11-05 14:22:15 UTC'`

### Step 3: Restore Base Backup
Restore the most recent base backup taken before the target time:
```bash
pg_restore -d scenesteward_prod --clean /var/backups/base_backup.dump
```

### Step 4: Configure `recovery.signal`
Place `recovery.signal` in the PostgreSQL data directory:
```bash
touch /var/lib/postgresql/data/recovery.signal
```

In `postgresql.auto.conf` or `recovery.conf`:
```ini
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2026-11-05 14:22:15 UTC'
recovery_target_action = 'promote'
```

### Step 5: Start PostgreSQL Engine
```bash
docker compose -f docker-compose.prod.yml start db
```
Monitor logs as PostgreSQL replays WAL files up to the target time:
```bash
docker compose -f docker-compose.prod.yml logs -f db
```
Once recovery promotes the instance to primary, `recovery.signal` is automatically removed.

### Step 6: Post-Recovery Validation
Verify table counts, RLS policies, and database trust handshake before starting the API.
