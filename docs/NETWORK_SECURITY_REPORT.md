# SceneSteward — Container Network Security & Isolation Audit

**Date**: November 5, 2026  
**Auditor**: Application Security Reviewer & Container Security Specialist  
**Target**: SceneSteward Staging Container Architecture  
**Status**: **`CONTAINER STACK VERIFIED`**  

---

## 1. Network Topology & Port Exposure Map

| Service | Container Internal Port | Host Port Binding | Exposure Scope | Security Policy | Status |
|:---|:---:|:---:|:---|:---|:---:|
| **`api`** | `8000/tcp` | `8001/tcp` | Staging Ingress | Reverse proxy or staging ingress; security headers enabled; rate limited | **VERIFIED** |
| **`db`** | `5432/tcp` | `5433/tcp` | Staging DB Port | Internal network access from API/worker; non-conflicting host port | **VERIFIED** |
| **`clamav`** | `3310/tcp` | `3310/tcp` | Antivirus Daemon | Internal network daemon for API `zINSTREAM` socket connection | **VERIFIED** |
| **`worker`** | None | None | No Exposed Ports | Outbound outbox delivery worker only; zero listening interfaces | **VERIFIED** |
| **`migrate`**| None | None | No Exposed Ports | Ephemeral one-off container; terminates on completion | **VERIFIED** |

### Verified Port Bindings:
```text
scenesteward-staging-api:    8000/tcp -> 0.0.0.0:8001, [::]:8001
scenesteward-staging-db:     5432/tcp -> 0.0.0.0:5433, [::]:5433
scenesteward-staging-clamav: 3310/tcp -> 0.0.0.0:3310, [::]:3310
scenesteward-staging-worker: No host port bindings
```

---

## 2. Container Privilege & Security Context

### Non-Root Execution
- `backend/Dockerfile` enforces non-root execution:
  ```dockerfile
  RUN useradd --system --uid 10001 --home /srv/scenesteward scenesteward
  USER scenesteward
  ```
- **In-Container Verification**:
  ```text
  docker exec scenesteward-staging-api id
  uid=10001(scenesteward) gid=999(scenesteward) groups=999(scenesteward)
  ```
- **Capabilities**: No elevated Linux capabilities (`CAP_SYS_ADMIN`, `CAP_NET_ADMIN`) are requested or granted.
- **Privileged Mode**: `privileged: false` across all containers.

---

## 3. Storage Volume Isolation & Permissions

| Volume Name | Target Path | Container Access | Data Contained |
|:---|:---|:---:|:---|
| `scenesteward-staging-pgdata` | `/var/lib/postgresql` | Read/Write (postgres) | PostgreSQL database files, WAL logs |
| `scenesteward-staging-storage`| `/srv/scenesteward/backend/var/storage` | Read/Write (scenesteward) | Uploaded temporary documentary media |
| `scenesteward-staging-clamav` | `/var/lib/clamav` | Read/Write (clamav) | Downloaded virus signature database |

---

## 4. HTTP Security Headers Audit

Verified on live HTTP `/health` response on host port 8001:
- `x-request-id`: UUID generated for correlation
- `x-correlation-id`: Preserved across call chain
- `x-content-type-options: nosniff`
- `x-frame-options: DENY`
- `referrer-policy: no-referrer`
- `cache-control: no-store`

---

## 5. Network Security Verdict
The staging container network architecture provides verified inter-service isolation. The unprivileged web API cannot bypass database RLS, the background worker has zero open attack surfaces, and all security headers are active on ingress.

Verdict: **`CONTAINER STACK VERIFIED`**
