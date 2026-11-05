# SceneSteward Runbook 03: Database Migration Runbook

**Document ID:** `RB-03-DATABASE-MIGRATION`  
**Target Environment:** Staging, Production  
**Audience:** Database Engineers, Backend Developers  

---

## 1. Principles & Policies
1. **Never auto-migrate on API boot**: Application containers must NOT have permissions to alter schemas or run migrations.
2. **Schema Owner Role Only**: Migrations execute exclusively under `scenesteward` (superuser/owner), never `scenesteward_app`.
3. **Forward-Compatible Migrations**: Changes must be additive and compatible with the running application version.
4. **Mandatory Pre-Migration Backup**: Always execute a pg_dump backup prior to applying schema migrations.

---

## 2. Migration Execution Process

### Step 1: Check Current Database Revision
```bash
alembic -c backend/alembic.ini current
```

### Step 2: Review Pending Migrations
```bash
alembic -c backend/alembic.ini history --verbose
```

### Step 3: Execute Pre-Migration Backup
```bash
python -m scripts.backup_database
```

### Step 4: Apply Pending Migrations
Using the isolated migrate container:
```bash
docker compose --env-file backend/.env.production -f docker-compose.prod.yml up --abort-on-container-exit migrate
```
Or via CLI:
```bash
alembic -c backend/alembic.ini upgrade head
```

### Step 5: Verify Schema Permissions
Verify that runtime role `scenesteward_app` has permissions on any newly created tables/sequences:
```sql
GRANT USAGE ON SCHEMA public TO scenesteward_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scenesteward_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scenesteward_app;
```

---

## 3. Handling Failed Migrations
If an Alembic migration aborts halfway:
1. Inspect Alembic logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs migrate
   ```
2. Determine if the failure was in a transaction block (PostgreSQL DDL is transactional).
3. If the transaction rolled back cleanly, resolve the error in the migration script and re-run.
4. If schema state is indeterminate, restore from the pre-migration backup following `RB-06-DATABASE-BACKUP-AND-RESTORE`.
