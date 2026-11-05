# SceneSteward Runbook 08: Disaster Recovery Procedures

**Document ID:** `RB-08-DISASTER-RECOVERY`  
**Target Environment:** Production  
**Audience:** Incident Commanders, Infrastructure Leads  

---

## 1. Disaster Scenarios
1. **Host Server Failure**: Physical hardware or cloud VM permanently lost.
2. **Datacenter / Region Outage**: Entire cloud region unavailable.
3. **Database Volume Corruption**: Unrecoverable corruption on storage volumes.

---

## 2. Recovery Objectives
- **Recovery Point Objective (RPO)**: < 15 minutes (data lost limited to latest WAL window).
- **Recovery Time Objective (RTO)**: < 30 minutes (full platform restored and accepting traffic).
- **Measured Local RTO**: 0.39 seconds (verified via `verify_isolated_restore.py`).

---

## 3. Full Secondary Site Disaster Recovery

### Step 1: Provision Clean Host
Boot target VM/instance with Docker and Docker Compose installed. Clone the repository and checkout `main`:
```bash
git clone https://github.com/nikhillakra2007-tech/SceneSteward.git /srv/scenesteward
cd /srv/scenesteward
```

### Step 2: Restore Configuration and Secrets
Fetch encrypted secrets from secure vault / offsite backup:
- `backend/.env.production`
- Database credentials and `DATABASE_IDENTITY_SECRET`
- `APP_ENCRYPTION_KEY`

### Step 3: Fetch Latest Offsite Database Backup
```bash
aws s3 cp s3://scenesteward-dr-backups/latest/scenesteward_prod.dump var/backups/
```

### Step 4: Boot Infrastructure Daemons
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d db redis clamav
```

### Step 5: Restore Database
```bash
python -m scripts.restore_database \
  --backup-file var/backups/scenesteward_prod.dump \
  --target-db scenesteward_prod \
  --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
```

### Step 6: Boot Application & Verify
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d api worker
curl -i http://127.0.0.1:8000/health/ready
```

### Step 7: Shift DNS Ingress
Update DNS record or load balancer target group to point to the new disaster recovery host.
