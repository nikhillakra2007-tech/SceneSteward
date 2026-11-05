# SceneSteward Runbook 04: Zero-Downtime Deployment

**Document ID:** `RB-04-ZERO-DOWNTIME-DEPLOYMENT`  
**Target Environment:** Production  
**Audience:** SREs, Release Engineers  

---

## 1. Zero-Downtime Architecture
SceneSteward achieves zero-downtime releases through:
1. **Backward-Compatible Database Migrations**: Database changes use the expand-contract pattern (add column as nullable -> deploy code that populates column -> backfill -> make column NOT NULL in next release).
2. **Graceful Connection Draining**: Uvicorn handles `SIGTERM` gracefully, finishing in-flight requests within a 30-second shutdown window.
3. **Dual-Container Rolling Replacement**: Running behind an upstream reverse proxy (e.g., NGINX, Traefik, AWS ALB), individual API workers or containers are replaced sequentially.

---

## 2. Step-by-Step Rolling Deployment

### Phase 1: Apply Additive Schema Updates
Execute the migration container while current API containers are live. Because all migrations are backward-compatible, running API instances continue normal operations without interruption.

### Phase 2: Rolling Container Update
1. Build the new image with release tag: `scenesteward-backend:v1.2.0`.
2. Start the secondary API container or reload Uvicorn workers:
   ```bash
   # Send SIGHUP to Uvicorn master process to gracefully reload worker processes
   kill -HUP $(pgrep -f "uvicorn app.main:app")
   ```
3. For multi-container environments:
   - Drain traffic from Container A at the load balancer.
   - Stop Container A: `docker stop scenesteward-api-a`.
   - Update and start Container A: `docker start scenesteward-api-a`.
   - Wait for `/health/ready` to return HTTP 200 on Container A.
   - Re-enable Container A in the load balancer.
   - Repeat for Container B.

---

## 3. Worker Reload
The background worker (`switch_retry.py`) completes its current batch of outbox messages before terminating on `SIGTERM`. Restart the worker container cleanly:
```bash
docker compose -f docker-compose.prod.yml restart worker
```
