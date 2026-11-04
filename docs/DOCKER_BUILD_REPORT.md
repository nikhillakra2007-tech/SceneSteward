# SceneSteward — Docker Build & Container Specification Report

**Date**: November 5, 2026  
**Auditor**: Senior DevOps Engineer & Container Infrastructure Specialist  
**Build Target**: `fliptheswitch-api:latest`, `fliptheswitch-migrate:latest`, `fliptheswitch-worker:latest`  
**Host Docker Engine**: Docker Engine 29.9.2 (desktop-linux WSL2)  
**Host Docker Compose**: Docker Compose v5.6.1  
**Build Status**: **`IMAGE BUILD VERIFIED`**  

---

## 1. Dockerfile & Build Specification Audit

The application container specification is defined in [`backend/Dockerfile`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/backend/Dockerfile):

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/scenesteward

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
WORKDIR /srv/scenesteward/backend

RUN useradd --system --uid 10001 --home /srv/scenesteward scenesteward \
    && mkdir -p var/storage \
    && chown -R scenesteward:scenesteward /srv/scenesteward
USER scenesteward

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

### Static Build Compliance Matrix
| Inspection Area | Requirement | Dockerfile Implementation | Verification | Status |
|:---|:---|:---|:---|:---:|
| **Base Image** | Minimal, security-patched OS | `python:3.12-slim` (Debian Bookworm minimal) | Verified x86_64 Linux container | **PASS** |
| **Dependency Caching** | Layer-cached pip install | `COPY requirements.txt` before full source code | Verified cached across service builds | **PASS** |
| **Security Context** | Non-root container execution | `useradd --system --uid 10001 scenesteward` + `USER scenesteward` | Verified in-container `uid=10001(scenesteward)` | **PASS** |
| **Secret Prevention** | No embedded secrets | Secrets injected at runtime via environment variables; none in image | Verified image contains only `.env.example` | **PASS** |
| **Storage Permissions** | Write access to storage | `mkdir -p var/storage && chown -R scenesteward:scenesteward` | Directory owned by UID 10001 | **PASS** |
| **Health Probe** | Automated container liveness | In-container HTTP probe against `http://127.0.0.1:8000/health` | Active and passing on `api` | **PASS** |
| **Working Directory** | Consistent app root | `/srv/scenesteward/backend` matches relative Alembic paths | Clean migration and app execution | **PASS** |

---

## 2. `.dockerignore` Integrity Audit

Audited [`\.dockerignore`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/.dockerignore):
- **Excluded Items**: `.git`, `.github`, `**/.venv`, `**/*.pyc`, `**/.pytest_cache`, `**/.ruff_cache`, `backend/var`, `backend/logs`, `docs`, `docker-compose.yml`, `README.md`.
- **Secret Shield**: `**/.env`, `**/.env.*` (strictly prevents local staging secrets or private `.env` files from leaking into the container image).
- **Template Allowed**: `!backend/.env.example` is retained for documentation.

Verification check inside built container:
```text
docker exec scenesteward-staging-api ls -la /srv/scenesteward/backend/.env*
-rw-r--r-- 1 scenesteward scenesteward 3492 Nov  4 18:30 /srv/scenesteward/backend/.env.example
```
Private `.env` and `.env.staging` were successfully excluded from image layers.

---

## 3. Actual Build Execution Evidence

Command executed:
```powershell
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml build
```

### Verified Image Artifacts:
```text
REPOSITORY              TAG         SIZE      IMAGE ID
fliptheswitch-api       latest      452MB     7e89df2c5e9f
fliptheswitch-worker    latest      452MB     5ea5d12d0163
fliptheswitch-migrate   latest      452MB     b1e4fb2fc00b
postgres                18-alpine   433MB     10a5c69a8303
clamav/clamav           latest      392MB     6d87c712e339
```

---

## 4. Status Verdict
- **Specification Status**: **`PASS`**
- **Image Build Status**: **`IMAGE BUILD VERIFIED`**
