# SceneSteward — Container Runtime & Environment Readiness Report

**Date**: November 5, 2026  
**Auditor**: Senior DevOps Engineer & Container Specialist  
**Host Engine**: Docker Engine 29.9.2 (desktop-linux WSL2)  
**Host Compose**: Docker Compose v5.6.1  
**Runtime Assessment**: **`CONTAINER STACK VERIFIED`**  

---

## 1. Host Docker Runtime Diagnostic Checks

All required container runtime capabilities were verified directly on the host machine:

| Diagnostic Check | Inspection Command | Actual Output / Observation | Status |
|:---|:---|:---|:---:|
| **Docker CLI** | `docker --version` | `Docker version 29.9.2, build 9920150` | **PASS** |
| **Docker Engine** | `docker info` | Context `desktop-linux`, 16 CPUs, 8.16 GB RAM | **PASS** |
| **Docker Compose v2**| `docker compose version` | `Docker Compose version v5.6.1-desktop.1` | **PASS** |
| **WSL2 Subsystem** | `docker context show` | Active context `desktop-linux` | **PASS** |
| **Available Disk Space**| `Get-PSDrive C` | **596 GB Free** | **PASS** |
| **Staging DB Port** | Test Port 5433 | `0.0.0.0:5433` -> `scenesteward-staging-db` | **PASS** |
| **Staging API Port** | Test Port 8001 | `0.0.0.0:8001` -> `scenesteward-staging-api` | **PASS** |
| **ClamAV Daemon Port**| Test Port 3310 | `0.0.0.0:3310` -> `scenesteward-staging-clamav` | **PASS** |

---

## 2. Docker Compose Staging Service Topology

The complete containerized runtime stack is specified in [`docker-compose.staging.yml`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docker-compose.staging.yml):

```
+---------------------------------------------------------------------------------+
| scenesteward-staging-net (Isolated Bridge Network)                              |
|                                                                                 |
|  +--------------------+         +--------------------+                          |
|  | db:5432            |<--------+ migrate (Alembic)  | (ephemeral init task)    |
|  | postgres:18-alpine |         +--------------------+                          |
|  +---------+----------+                                                         |
|            |                                                                    |
|            | health: pg_isready                                                 |
|            v                                                                    |
|  +---------+----------+         +--------------------+                          |
|  | api:8000           |<--------+ clamav:3310        |                          |
|  | FastAPI (UID 10001)|         | clamav/clamav      |                          |
|  +---------+----------+         +--------------------+                          |
|            | health: /health                                                    |
|            v                                                                    |
|  +---------+----------+                                                         |
|  | worker             | (switch_retry.py outbox daemon, restart: always)       |
|  +--------------------+                                                         |
+---------------------------------------------------------------------------------+
```

---

## 3. Actual Live Runtime Evidence (`docker compose ps`)

```text
NAME                          IMAGE                  COMMAND                  SERVICE   STATUS                    PORTS
scenesteward-staging-api      fliptheswitch-api      "uvicorn app.main:ap…"   api       Up 10 minutes (healthy)   0.0.0.0:8001->8000/tcp
scenesteward-staging-clamav   clamav/clamav:latest   "/init"                  clamav    Up 15 minutes (healthy)   0.0.0.0:3310->3310/tcp
scenesteward-staging-db       postgres:18-alpine     "docker-entrypoint.s…"   db        Up 10 minutes (healthy)   0.0.0.0:5433->5432/tcp
scenesteward-staging-worker   fliptheswitch-worker   "python scripts/swit…"   worker    Up 2 minutes (healthy)    8000/tcp
```

### In-Container Process Security:
```text
UID        PID  PPID  C STIME TTY          TIME CMD
10001        1     0  0 19:07 ?        00:00:01 uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```
- Non-root execution verified: `UID 10001 (scenesteward)`.
- Internal network communication verified over `scenesteward-staging-net`.

---

## 4. Container Runtime Conclusion & Operational Verdict
All 4 staging containers (`api`, `db`, `clamav`, `worker`) and the ephemeral migration runner (`migrate`) have successfully initialized, achieved verified health probe status, and are operational.

Operational Verdict: **`CONTAINER STACK VERIFIED`**
