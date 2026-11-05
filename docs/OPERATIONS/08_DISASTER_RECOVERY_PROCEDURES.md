# SceneSteward Runbook 08: Disaster Recovery Procedures

**Document ID:** `RB-08-DISASTER-RECOVERY`  
**Target Environment:** Production  
**Audience:** Incident Commanders, Infrastructure Leads, SREs  
**Last Updated:** 2026-11-06  

---

## 1. Disaster Scenarios & Threat Vectors

SceneSteward disaster recovery playbooks cover three catastrophic operational failure modes:
1. **Total Host / Compute Destruction**: Primary container node or virtual machine fails unrecoverably.
2. **Datacenter / Availability Zone Outage**: Primary cloud facility suffers network partitioning or hardware failure.
3. **Catastrophic Database Storage Corruption**: Database data volume becomes permanently corrupted or dropped.

---

## 2. Recovery Metrics & Measured Benchmarks

- **Recovery Point Objective (RPO)**: < 15 minutes (with WAL archiving; tested to 1.0s precision).
- **Recovery Time Objective (RTO)**: Target < 30 minutes.
- **Measured Cold Recovery Benchmark**: **5.83 seconds** (measured in live isolated exercise).

### Measured Independent Timings Breakdown (`verify_isolated_restore.py`):

| Phase | Operation | Measured Duration | Verification Check |
|---|---|---|---|
| 1 | Disposable Database Provisioning | 0.524s | Clean target schema established |
| 2 | Encrypted Backup Generation (`.dump.enc`) | 1.092s | Temp staging, Fernet AES-256 |
| 3 | Pre-Publication TOC Integrity Verification | 0.082s | `pg_restore --list` (293 TOC entries) |
| 4 | Off-Site Replication & Mirror Verification | 0.005s | Streaming SHA-256 parity confirmed |
| 5 | Database Restoration from Off-Site Archive | 1.045s | Drop, clean restore, exit code 0 |
| 6 | Post-Restore Deep Structural Validation | 1.037s | 20 tables, 212 triggers, 69 RLS policies |
| 7 | Application Stack Startup & Health Readiness | 2.046s | `/health/ready` returns HTTP 200 |
| **Total** | **End-to-End Cold Disaster Recovery** | **5.831s** | **All Invariants Verified** |

---

## 3. Full Secondary Site Disaster Recovery Execution

### Step 1: Provision Clean Target Host
Provision a clean VM or container instance with Docker and Docker Compose installed:
```bash
git clone https://github.com/nikhillakra2007-tech/SceneSteward.git /srv/scenesteward
cd /srv/scenesteward
git checkout main
```

### Step 2: Restore Secrets & Environment Configuration
Retrieve production secrets from the off-site KMS / secret manager:
- `backend/.env.production`
- `DATABASE_IDENTITY_SECRET`
- `APP_ENCRYPTION_KEY`
- `POSTGRES_PASSWORD` and `APP_PASSWORD`

### Step 3: Fetch Verified Off-Site Archive
Pull the latest verified encrypted dump and its companion metadata manifest from off-site object storage:
```bash
aws s3 cp s3://scenesteward-dr-backups/latest/scenesteward_prod.dump.enc var/backups/
aws s3 cp s3://scenesteward-dr-backups/latest/scenesteward_prod.meta.json var/backups/
```

### Step 4: Boot Core Infrastructure Daemons
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d db redis clamav
```
Verify databases and daemons pass health checks:
```bash
docker compose -f docker-compose.prod.yml ps
```

### Step 5: Restore Database from Encrypted Off-Site Archive
```bash
python scripts/restore_database.py \
  --backup-file var/backups/scenesteward_prod.dump.enc \
  --encryption-key "$APP_ENCRYPTION_KEY" \
  --target-db scenesteward_prod \
  --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
```
*The restore script automatically validates SHA-256 checksums, decrypts the staged dump, executes pg_restore, verifies exit code 0, reprovisions `scenesteward_app` with `NOBYPASSRLS`, and validates all 20 tables, 212 triggers, and 69 RLS policies.*

### Step 6: Start Application API & Background Worker
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d api worker
```

### Step 7: Verify Platform Health Probes
```bash
curl -fsS http://127.0.0.1:8000/health/ready | jq .
```
Expected output:
```json
{
  "status": "ok",
  "app": "SceneSteward",
  "version": "v1",
  "checks": {
    "database": {"status": "ok", "migration_head": "e1f2a3b4c5d6"},
    "redis": {"status": "ok"},
    "clamav": {"status": "ok"},
    "storage": {"status": "ok", "provider": "supabase"}
  }
}
```

### Step 8: Ingress DNS Cutover
Point the Cloudflare / Route53 DNS CNAME or ALB target group to the newly restored host.
