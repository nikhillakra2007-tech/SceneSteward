# SceneSteward Runbook 13: Container Security & Patching

**Document ID:** `RB-13-CONTAINER-SECURITY`  
**Target Environment:** All Environments  
**Audience:** DevSecOps Engineers  

---

## 1. Container Hardening Baselines
- **Unprivileged Runtime**: Backend Dockerfile creates and runs as unprivileged user `scenesteward:scenesteward` (UID/GID 10001). Containers NEVER run as `root`.
- **Minimal Base Images**: Uses `python:3.12-slim`, `postgres:16-alpine`, `redis:7-alpine`.
- **Pinned Dependencies**: Explicit package versions in `requirements.txt` and pinned base image versions (avoiding `latest`).
- **Resource Constraints**: CPU and Memory quotas enforced via Compose `deploy.resources.limits` to prevent noisy-neighbor and DoS attacks.

---

## 2. Vulnerability Scanning Workflow
Automated vulnerability scanning with Trivy:
```bash
# Scan base images and dependencies
trivy image --severity HIGH,CRITICAL scenesteward-backend:production
trivy fs --security-checks vuln,config .
```

---

## 3. Patching Procedure

### Python Vulnerability Patching:
1. Update dependency in `backend/requirements.txt` or `requirements-dev.txt`.
2. Run pytest suite and ruff checks locally:
   ```bash
   pytest backend/tests
   ruff check backend
   ```
3. Rebuild container and test in staging before deploying to production.

### Base OS / Base Image Patching:
1. Update Dockerfile `FROM python:3.12.x-slim`.
2. Re-test build:
   ```bash
   docker build -f backend/Dockerfile -t scenesteward-backend:patch .
   ```
