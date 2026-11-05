# SceneSteward Runbook 07: Point-in-Time Recovery (PITR)

**Document ID:** `RB-07-PITR`  
**Target Environment:** Production  
**Audience:** Principal Database Administrators, SREs  
**Last Updated:** 2026-11-06  

---

## 1. Principles & Recovery Objectives

Point-in-Time Recovery (PITR) enables restoring the SceneSteward database state to an exact historical microsecond, undoing accidental deletions, malicious corruption, or destructive application bugs while preserving all transactions committed before the incident target.

- **Recovery Point Objective (RPO)**: < 15 minutes (under continuous WAL archiving; tested to 1.0s precision in automated exercises).
- **Recovery Time Objective (RTO)**: < 30 minutes for databases up to 100 GB.
- **Underlying Architecture**: Base physical/logical backup snapshot + continuous Write-Ahead Log (WAL) archiving to independent off-site storage.

---

## 2. Infrastructure Architecture Options

### Option A: Managed Cloud PostgreSQL (AWS RDS / Supabase / GCP Cloud SQL)
When deployed on managed PostgreSQL infrastructure:
- Continuous physical streaming replication to multi-AZ replicas is enabled by default.
- Automated WAL shipping to durable object storage (e.g. AWS S3 or Google Cloud Storage) provides point-in-time rewind with 1-second granularity for the configured retention period (default: 30 days).
- Recovery target time is selected in the cloud console or CLI (`aws rds restore-db-instance-to-point-in-time --restore-time "2026-11-06T14:22:15Z"`).

### Option B: Self-Hosted Docker / Bare-Metal PostgreSQL 16
For self-hosted instances, configure continuous WAL archiving in `postgresql.conf`:
```ini
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f'
archive_timeout = 900  # 15 minutes maximum lag between forced WAL switches
```
Ensure `/var/lib/postgresql/wal_archive` is mounted to an independent EBS volume or synchronized continuously to object storage via tools like `pgBackRest` or `wal-g`.

---

## 3. Operational PITR Execution Procedure

### Step 1: Quarantine Ingress & Freeze Traffic
Immediately stop the API and worker containers to prevent further writes or state drift:
```bash
docker compose -f docker-compose.prod.yml stop api worker
```

### Step 2: Establish Precise Target Timestamp ($T_{target}$)
Identify the exact UTC timestamp immediately preceding the disaster event (e.g. through the immutable audit log or PostgreSQL transaction logs):
```
T_target = '2026-11-06 14:22:15 UTC'
```

### Step 3: Restore Pre-Target Base Snapshot
Restore the closest base backup archive created before $T_{target}$:
```bash
python scripts/restore_database.py \
  --backup-file var/backups/scenesteward_prod_20261106_120000Z.dump \
  --target-db scenesteward_prod \
  --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
```

### Step 4: Configure PostgreSQL Recovery Replay Signal
Place `recovery.signal` in the PostgreSQL data directory:
```bash
touch /var/lib/postgresql/data/recovery.signal
```

Append recovery directives to `/var/lib/postgresql/data/postgresql.auto.conf`:
```ini
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2026-11-06 14:22:15 UTC'
recovery_target_action = 'promote'
```

### Step 5: Start PostgreSQL Database Service
```bash
docker compose -f docker-compose.prod.yml start db
```
Monitor WAL replay progress:
```bash
docker compose -f docker-compose.prod.yml logs -f db
```
Once WAL replay reaches $T_{target}$, PostgreSQL automatically promotes itself to read-write primary and deletes `recovery.signal`.

### Step 6: Post-Recovery Integrity Handshake
Execute post-recovery validation to verify schema integrity, least-privilege roles, and database identity secret match:
```bash
python -c "from app.core.database import verify_database_trust; res = verify_database_trust(); assert res.get('ok'), res"
```

### Step 7: Resume Application Stack
```bash
docker compose -f docker-compose.prod.yml start api worker
```

---

## 4. Automated PITR Verification Drill

SceneSteward includes an automated verification script that executes a complete PITR exercise in an isolated database environment:

```bash
APP_ENV=test python backend/scripts/verify_pitr_recovery.py
```

### Automated Drill Workflow:
1. **Provisioning**: Spawns clean sandbox database `scenesteward_pitr_exercise_test`.
2. **Batch 1 (Pre-Target Data at $T_1$)**: Writes project and two participant records (Alpha, Beta).
3. **Snapshot ($T_{target}$)**: Captures point snapshot at exact UTC time $T_{target}$.
4. **Batch 2 (Post-Target Data at $T_2$)**: Writes third participant record (Gamma).
5. **Catastrophic Disaster Simulation ($T_{destructive}$)**: Destructively drops participant records and marks project corrupted.
6. **PITR Recovery**: Restores database state strictly to target $T_{target}$.
7. **Verification**: Proves Alpha and Beta exist, Gamma is absent, corruption is reversed, and cryptographic trust handshake succeeds.
8. **Measured Precision**: Demonstrates temporal resolution $\le 1.0\text{s}$.
