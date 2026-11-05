# SceneSteward Runbook 10: Rollback Procedures

**Document ID:** `RB-10-ROLLBACK`  
**Target Environment:** Staging, Production  
**Audience:** Release Leads, DevOps Engineers, SREs  
**Last Updated:** 2026-11-06  

---

## 1. When to Initiate Rollback
A release must be aborted and rolled back immediately if any of the following occur:
1. Smoke tests fail post-deployment.
2. `/health/ready` returns HTTP 503 for > 3 minutes post-startup.
3. Unhandled error rate exceeds 1% of total requests over a 5-minute window.
4. Database RLS trust boundary verification fails (`public.app_verify_trust_handshake` returns false).
5. Runtime role least-privilege startup check rejects superuser or bypassrls permissions.

---

## 2. Code & Container Rollback (No Schema Changes)

If the database schema was not modified:
```bash
# Step 1: Repoint image tag in compose or environment to previous known-good release
export RELEASE_TAG=v1.1.9

# Step 2: Restart API and worker with previous image
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d api worker

# Step 3: Verify health
curl -fsS http://127.0.0.1:8000/health/ready || echo "Rollback failed health probe!"
```

---

## 3. Database Migration Rollback

If the failed release applied an Alembic migration:

### Scenario A: Reversible Additive Migration
If the migration has a clean `downgrade()` implementation:
```bash
# Downgrade one revision using migration owner URL
alembic -c backend/alembic.ini downgrade -1

# Verify current revision
alembic -c backend/alembic.ini current

# Re-enforce least-privilege role permissions
python scripts/provision_db_roles.py --db-url "$MIGRATION_DATABASE_URL"
```

### Scenario B: Irreversible or Corrupted Schema
If the migration corrupted data or schema state:
1. **Stop API & Worker Containers**:
   ```bash
   docker compose -f docker-compose.prod.yml stop api worker
   ```
2. **Restore from Pre-Deployment Backup**:
   ```bash
   python scripts/restore_database.py \
     --backup-file var/backups/pre_deploy_backup.dump \
     --target-db scenesteward_prod \
     --confirm-destructive-override I_KNOW_THIS_DROPS_AND_OVERWRITES_DATA
   ```
3. **Verify Restored Schema and Role Permissions**:
   ```bash
   python scripts/provision_db_roles.py --db-url "$MIGRATION_DATABASE_URL"
   ```
4. **Restart Stack with Previous Application Image**:
   ```bash
   docker compose --env-file backend/.env.production -f docker-compose.prod.yml up -d api worker
   ```
5. **Verify Readiness Probe**:
   ```bash
   curl -fsS http://127.0.0.1:8000/health/ready | jq .
   ```
