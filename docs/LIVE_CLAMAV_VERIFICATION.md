# SceneSteward — Live ClamAV Antivirus Staging Activation Report

**Date**: November 4, 2026  
**Auditor**: Application Security Reviewer & Systems Reliability Engineer  
**Subsystem**: ClamAV Antivirus Daemon (TCP `INSTREAM` Protocol)  
**Current Verification State**: **`DAEMON PENDING (BLOCKED LIVE)`**  

---

## 1. Technical Invariants & Protocol Specification

Uploaded documentary media (contracts, signed releases, treatment documents) undergo malware inspection before being finalized in storage.
The scanner (`backend/app/services/malware_scanner.py`) enforces:
1. **TCP `INSTREAM` Protocol**:
   - Sends `zINSTREAM\0` command over a TCP socket to `CLAMAV_HOST:CLAMAV_PORT` (default port 3310).
   - Streams chunks prefixed by 4-byte network-endian length integers.
   - Terminates with a 0-length chunk (`struct.pack("!I", 0)`).
2. **Response Handling**:
   - `stream: OK` -> `ScanStatus.CLEAN`
   - `stream: <virus> FOUND` -> `ScanStatus.INFECTED` (upload rejected with HTTP 422).
3. **Fail-Closed Operation (`ANTIVIRUS_FAIL_CLOSED=true`)**:
   - If the scanner daemon times out or the TCP connection is refused, uploads are rejected with HTTP 503 (`PreconditionFailed: Malware scanner unavailable`), preventing uninspected files from entering the documentary repository.

---

## 2. Test Execution & Diagnostic Output

### Local & Synthetic Verification
- **Automated Tests**:
  - `backend/tests/integration/test_documents.py` (`test_malware_file_detected_and_rejected`)
  - `backend/tests/integration/test_failure_modes.py` (`test_clamav_unavailable_fail_closed`)
  - Tests confirm EICAR signature quarantine, decompression bomb rejection, and fail-closed 503 responses.

### Live Staging Probe Execution
- **Command**:
  ```powershell
  $env:PYTHONPATH = "backend"
  .\backend\.venv\Scripts\python.exe backend/scripts/verify_staging_clamav.py
  ```
- **Actual Terminal Output**:
  ```
  ============================================================
  SceneSteward — Staging ClamAV Daemon Verification
  ============================================================
  Antivirus Provider: mock
  ClamAV Host: 127.0.0.1
  ClamAV Port: 3310
  Fail-Closed Mode: False

  [1/3] Testing TCP connection to 127.0.0.1:3310 ...
  [RESULT] BLOCKED: ClamAV daemon is not reachable on 127.0.0.1:3310 ([WinError 10061] No connection could be made because the target machine actively refused it)
  ```

---

## 3. Classification & Next Actions

- **Current State**: `MOCK TESTED / DAEMON PENDING (BLOCKED LIVE)`
- **Remediation Steps**:
  1. Start the ClamAV daemon container:
     ```powershell
     docker run -d --name scenesteward-clamav -p 3310:3310 clamav/clamav:latest
     ```
     *(Or start the `clamav` service defined in `docker-compose.staging.yml`)*
  2. In `backend/.env.staging`:
     ```env
     ANTIVIRUS_PROVIDER=clamav
     CLAMAV_HOST=127.0.0.1
     CLAMAV_PORT=3310
     ANTIVIRUS_FAIL_CLOSED=true
     ```
  3. Re-run `python backend/scripts/verify_staging_clamav.py` to verify TCP ping, clean probe, and EICAR detection.

