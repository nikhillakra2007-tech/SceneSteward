# SceneSteward — Deployment & Operational Acceptance Report

**Date**: November 4, 2026  
**Auditor**: Site Reliability Engineer & DevSecOps Engineer  
**Scope**: Containerization, Service Orchestration, Observability, Health Checks, Worker Operations  
**Verification Result**: **PASS — STAGING CONTAINER READY**  

---

## 1. Container Security & Multi-Stage Build

### Dockerfile Inspection (`backend/Dockerfile`)
- **Base Image**: `python:3.12-slim-bookworm` (Debian minimal base with active security patches).
- **Security Context**:
  - Non-root execution: Container executes strictly under `USER appuser` (`UID 10001`, `GID 10001`).
  - No `sudo` or superuser privileges inside container.
  - Minimal package footprint: Build tools (`gcc`, `libpq-dev`) are isolated or cleaned up.
- **Healthcheck Configured**:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
  ```

---

## 2. Service Separation & Command Directives

SceneSteward supports independent, horizontally scalable execution of the web API and background worker processes:

### 2.1 Web API Service
- **Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
- **Endpoints**:
  - `GET /health`: Liveness probe (returns status 200 and component health).
  - `GET /api/v1/metrics`: Prometheus metrics scraper endpoint.
  - `GET /api/v1/...`: 48 REST API endpoints.

### 2.2 Background Outbox & Switch Retry Worker
- **Command**: `python backend/scripts/switch_retry.py`
- **Execution Model**: Polling daemon with exponential backoff and jitter for pending external deliveries.

---

## 3. Observability & Telemetry

1. **Structured JSON Logging**:
   Application logs are emitted in structured JSON format with correlation IDs, request paths, status codes, and execution latency.
2. **Prometheus Metrics**:
   - Implemented in `backend/app/api/v1/endpoints/metrics.py` and `backend/app/services/metrics.py`.
   - Exposes request counts, latency histograms, RLS denial counters, and outbox failure rates.
   - Tested in `backend/tests/integration/test_metrics.py` (2 tests passing).

---

## 4. Fail-Closed Configuration Enforcement
In `backend/app/core/config.py`:
- `APP_ENV=production` strictly enforces:
  - `AUTH_PROVIDER != "dev"`
  - High-entropy secrets for `DATABASE_IDENTITY_SECRET`, `JWT_SECRET`, and `FIELD_ENCRYPTION_KEY`.
  - Rejection of default or insecure development passwords.

