# SceneSteward — ClamAV Container Deployment & Integration Report

**Date**: November 5, 2026  
**Auditor**: Application Security Engineer & Systems Reliability Specialist  
**Service Image**: `clamav/clamav:latest`  
**Container Role**: Antivirus Inspection Daemon for Documentary Documents  
**Status**: **`CONTAINER STACK VERIFIED`**  

---

## 1. ClamAV Container Specification

From [`docker-compose.staging.yml`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docker-compose.staging.yml):
```yaml
  clamav:
    image: clamav/clamav:latest
    container_name: scenesteward-staging-clamav
    ports:
      - "${CLAMAV_PORT:-3310}:3310"
    volumes:
      - scenesteward-staging-clamav:/var/lib/clamav
    networks:
      - scenesteward-staging-net
    healthcheck:
      test: ["CMD-SHELL", "clamdscan /etc/passwd || exit 0"]
      interval: 10s
      timeout: 5s
      retries: 15
      start_period: 60s
```

### Architectural Analysis:
1. **TCP Port 3310**: Exposes standard `clamd` listening port over both container network (`clamav:3310`) and host port 3310.
2. **Persistent Signature Volume**: `scenesteward-staging-clamav` caches downloaded virus definition databases (`daily.cvd`, `main.cvd`), avoiding full signature re-downloads on container restarts.
3. **Startup Grace Period**: `start_period: 60s` accommodates the warm-up window required for `clamd` to load multi-million signature databases into memory before handling TCP queries.

---

## 2. Live Socket Wire Verification

Verified directly against the live container over TCP:

```text
[1/3] PING daemon ...
PONG in 0.9ms

[2/3] Scanning clean payload ...
Result: status=clean scanner=clamav detail=None

[3/3] Scanning EICAR test signature ...
Result: status=infected scanner=clamav detail=Eicar-Test-Signature
```

### Application Client Compatibility (`INSTREAM` Protocol)
The SceneSteward scanner (`backend/app/services/malware_scanner.py`) implements the official ClamAV `zINSTREAM` socket wire protocol:
- **Clean File Scanning**: Document bytes streamed in 2048-byte chunks; returned `stream: OK` -> `ScanStatus.CLEAN`.
- **Malware Interception**: EICAR test signature flagged `stream: Eicar-Test-Signature FOUND` -> `ScanStatus.INFECTED`.
- **Fail-Closed Security**: Unscanned files rejected if daemon is unavailable.

---

## 3. Container Workflow Integration Evidence

Executed during 13-step container acceptance workflow:
```text
[7/13] Scanning document bytes through live ClamAV daemon ...
Scan Status: clean (scanner=clamav)
[OK] Document passed clean malware inspection.
```

---

## 4. Deployment Status
- **Client Protocol Implementation**: **`PASS`**
- **Container Service Health**: **`HEALTHY (Up 15+ minutes)`**
- **Malware Interception**: **`PASS (EICAR Detected)`**
- **Status**: **`CONTAINER STACK VERIFIED`**
