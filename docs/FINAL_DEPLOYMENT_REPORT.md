# SceneSteward — Final Production Deployment & Infrastructure Report

**Date:** November 2026  
**Auditor:** Principal DevOps Engineer & Cloud Infrastructure Architect  
**Repository:** `nikhillakra2007-tech/SceneSteward`  

---

## 1. Deployment Topology & Compose Separation

SceneSteward maintains strict separation across environments:

1. **Development (`docker-compose.yml`):**
   - Streamlined stack with local PostgreSQL, live code reloading, and local mock adapters for rapid feature iteration.

2. **Staging (`docker-compose.staging.yml`):**
   - Staging candidate environment running PostgreSQL 18, ClamAV antivirus daemon, one-shot migration runner, and live provider verifiers.

3. **Production (`docker-compose.prod.yml`):**
   - Multi-container production stack with:
     - PostgreSQL 18 with encrypted persistent storage volumes (`scenesteward-prod-pgdata`).
     - Redis 7-alpine for distributed sliding-window token bucket rate limiting.
     - ClamAV antivirus daemon for document scanning with fail-closed enforcement.
     - One-shot Alembic migration container (`scenesteward-prod-migrate`) guaranteeing migrations finish before API startup.
     - FastAPI application service (`scenesteward-prod-api`) running non-root (`uid: 10001`), resource limits (2 CPUs, 2GB RAM), and health/readiness probes.
     - Asynchronous outbox worker service (`scenesteward-prod-worker`) with automatic restart policies.

---

## 2. Health & Readiness Probes

The API exposes unauthenticated, low-overhead health endpoints:
- `GET /health` & `GET /health/live`: Fast liveness check returning HTTP 200 OK.
- `GET /health/ready`: Deep readiness probe querying PostgreSQL connection pool status and returning degraded status if database connectivity fails.

---

## 3. Disaster Recovery & Verified Recovery Time Objective (RTO)

Disaster recovery capabilities have been verified on real PostgreSQL instances via `backend/scripts/verify_isolated_restore.py`:
- Atomic snapshot creation via `pg_dump` with table of contents integrity verification.
- Isolated restoration into clean disposable databases.
- Full verification of 20 tables, 212 triggers, 69 RLS policies, 18 RLS tables, and Fernet contact data decryption.
- **Measured RTO:** **0.29 seconds** recovery time objective.

---

## 4. Production Deployment Checklist

- [x] Dockerfile builds cleanly with non-root security context.
- [x] Secrets injected strictly via environment variables (never committed to repository).
- [x] Database migrations execute exactly once via init container.
- [x] Redis and ClamAV services healthy and integrated.
- [x] Rate limiting active across auth and token endpoints.
- [x] Next.js frontend compiled for production with static asset optimization.
