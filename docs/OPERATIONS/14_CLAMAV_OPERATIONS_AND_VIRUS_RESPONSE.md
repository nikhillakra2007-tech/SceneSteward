# SceneSteward Runbook 14: ClamAV Operations & Virus Response

**Document ID:** `RB-14-CLAMAV-OPERATIONS`  
**Target Environment:** Staging, Production  
**Audience:** Security Engineers, System Administrators  

---

## 1. Antivirus Daemon Architecture
- **Daemon**: `clamd` running in container `scenesteward-prod-clamav` listening on port `3310`.
- **Protocol**: Streaming `zINSTREAM` socket connection.
- **Fail-Closed Policy**: When `ANTIVIRUS_FAIL_CLOSED=true`, any file upload that fails antivirus inspection (daemon unreachable, timeout, or infected) is rejected immediately with HTTP 503 / 400.
- **Health Check**: Active ping (`ping_clamav`) sends `zPING\0` and expects `PONG\0`.

---

## 2. Signature Updates (FreshClam)
The ClamAV container runs `freshclam` in the background to automatically download virus definition updates (`daily.cvd`, `main.cvd`, `bytecode.cvd`).
Signatures persist across container restarts via volume:
`scenesteward-prod-clamav:/var/lib/clamav`

Force an immediate manual signature database update:
```bash
docker exec -it scenesteward-prod-clamav freshclam
```

---

## 3. Malware Detection Incident Response

When an uploaded document is flagged:
1. **Immediate Quarantine**: The upload stream is truncated and discarded; the file is never persisted to storage or database.
2. **Audit Event Logged**: `malware_scanner.py` records a warning with virus name (e.g., `Eicar-Signature`).
3. **Security Alert Triggered**: High-severity notification dispatched to the security team.
4. **IP Rate Limit**: The client IP is temporarily throttled to mitigate payload flooding.
