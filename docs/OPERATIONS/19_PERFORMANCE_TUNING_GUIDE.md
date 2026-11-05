# SceneSteward Runbook 19: Performance Tuning Guide

**Document ID:** `RB-19-PERFORMANCE-TUNING`  
**Target Environment:** Production  
**Audience:** SREs, Performance Engineers  

---

## 1. PostgreSQL Connection Pooling & Tuning
- **API Runtime Pool**:
  - `pool_size = 10` connections per worker process.
  - `max_overflow = 5` connections.
  - `pool_pre_ping = True` (detects stale connections).
  - `pool_recycle = 3600` (1 hour recycling).
- **PostgreSQL Server Tuning** (in `postgresql.conf`):
  - `max_connections = 100`
  - `shared_buffers = 512MB`
  - `effective_cache_size = 1536MB`
  - `work_mem = 16MB`
  - `maintenance_work_mem = 128MB`

---

## 2. Uvicorn & FastAPI Concurrency Tuning
- **Worker Count**: Set to `workers = 4` in production compose stack (appropriate for 2-4 vCPUs).
- **Process Model**: Multi-process worker model with asynchronous event loop per worker.
- **Proxy Headers**: `--proxy-headers` enabled to trust upstream reverse proxy headers for real client IP extraction.

---

## 3. High-Performance Query Optimization
- Keyset pagination is enforced on audit logs (`events`) to maintain constant $O(1)$ query times regardless of table depth.
- Indexes on RLS lookup keys: `(project_id)`, `(participant_id)`, `(agreement_id)`.
- RLS evaluation caching via transaction-local PostgreSQL settings (`set_config(..., true)`).
