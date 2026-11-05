# SceneSteward Runbook 10: Rollback Procedures

**Document ID:** `RB-10-ROLLBACK`  
**Target Environment:** Staging, Production  
**Audience:** Release Leads, DevOps Engineers  

---

## 1. When to Initiate Rollback
A release must be rolled back immediately if:
1. Smoke tests fail post-deployment.
2. `/health/ready` returns HTTP 503 for > 3 minutes post-startup.
3. Unhandled error rate exceeds 1% of total requests over a 5-minute window.
4. Database RLS trust boundary verification fails.

---

## 2. Code & Container Rollback (No Schema Changes)

If the database schema was not modified:
```bash
# Step 1: Repoint image tag in compose or environment to previous known-good release
export RELEASE_TAG=v1.1.9

# Step 2: Restart API and worker with previous image
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d api worker

# Step 3: Verify health
curl -f http://127.0.0.1:8000/health/ready || echo "Rollback failed health probe!"
```

---

## 3. Database Migration Rollback

If the failed release applied an Alembic migration:

### Scenario A: Reversible Additive Migration
If the migration has a clean `downgrade()` implementation:
```bash
# Downgrade one revision
alembic -c backend/alembic.ini downgrade -1

# Verify current revision
alembic -c backend/alembic.ini current
```

### Scenario B: Irreversible or Corrupted Schema
If the migration corrupted data or schema state:
1. Stop API containers:
   ```bash
   docker compose -f docker-compose.prod.yml stop api worker
   ```
2. Restore from the pre-deployment backup:
   ```bash
   python -m scripts.restore_database \
     --backup-file var/backups/pre_deploy_backup.dump \
     --target-db scenesteward_prod \
     --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
   ```
3. Start API containers with previous code version.
