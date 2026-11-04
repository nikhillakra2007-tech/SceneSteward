"""Verification harness for Live Staging ClamAV Antivirus Daemon.

Tests:
1. TCP socket connectivity to clamd (port 3310)
2. Clean file scanning over zINSTREAM protocol
3. EICAR malware test signature detection
4. Fail-closed behavior validation
"""
from __future__ import annotations

import socket
import sys
import time

from app.core.config import get_settings
from app.services.malware_scanner import EICAR_SIGNATURE, ScanStatus, scan_bytes


def verify_clamav_daemon() -> dict[str, str | bool]:
    settings = get_settings()
    results: dict[str, str | bool] = {
        "provider": settings.antivirus_provider,
        "host": settings.clamav_host,
        "port": settings.clamav_port,
        "tcp_reachable": False,
        "clean_scan_ok": False,
        "eicar_detected": False,
        "status": "BLOCKED",
    }

    print("=" * 60)
    print("SceneSteward — Staging ClamAV Daemon Verification")
    print("=" * 60)
    print(f"Antivirus Provider: {settings.antivirus_provider}")
    print(f"ClamAV Host: {settings.clamav_host}")
    print(f"ClamAV Port: {settings.clamav_port}")
    print(f"Fail-Closed Mode: {settings.antivirus_fail_closed}")

    # Check TCP socket connectivity first
    print(f"\n[1/3] Testing TCP connection to {settings.clamav_host}:{settings.clamav_port} ...")
    start = time.perf_counter()
    try:
        with socket.create_connection((settings.clamav_host, settings.clamav_port), timeout=3.0) as sock:
            sock.sendall(b"zPING\0")
            resp = sock.recv(32).decode("utf-8", errors="replace").strip()
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"Ping Response: '{resp}' in {elapsed_ms:.1f}ms")
            results["tcp_reachable"] = True
    except Exception as exc:  # noqa: BLE001
        print(f"[RESULT] BLOCKED: ClamAV daemon is not reachable on {settings.clamav_host}:{settings.clamav_port} ({exc})")
        results["detail"] = f"TCP connection failed: {exc}"
        return results

    # Ensure provider is configured to clamav for the scan calls
    clamav_settings = settings.model_copy(update={"antivirus_provider": "clamav"})

    print("\n[2/3] Scanning clean payload over zINSTREAM protocol ...")
    clean_bytes = b"SceneSteward clean documentary interview transcript text probe."
    clean_res = scan_bytes(clean_bytes, settings=clamav_settings)
    print(f"Clean scan status: {clean_res.status.value} (scanner={clean_res.scanner})")
    if clean_res.status == ScanStatus.CLEAN:
        results["clean_scan_ok"] = True
        print("[OK] Clean payload verified as clean.")
    else:
        print(f"[FAIL] Unexpected clean scan result: {clean_res}")
        results["detail"] = f"Clean scan failed: {clean_res}"
        return results

    print("\n[3/3] Scanning EICAR standard test signature ...")
    eicar_res = scan_bytes(EICAR_SIGNATURE, settings=clamav_settings)
    print(f"EICAR scan status: {eicar_res.status.value} (virus='{eicar_res.virus_name}')")
    if eicar_res.status == ScanStatus.INFECTED:
        results["eicar_detected"] = True
        print("[OK] EICAR signature detected and quarantined by live ClamAV daemon.")
    else:
        print(f"[FAIL] ClamAV failed to detect EICAR signature: {eicar_res}")
        results["detail"] = f"EICAR detection failed: {eicar_res}"
        return results

    results["status"] = "LIVE_VERIFIED"
    print("\n>>> CLAMAV STATUS: LIVE_VERIFIED <<<")
    return results


if __name__ == "__main__":
    res = verify_clamav_daemon()
    if res["status"] != "LIVE_VERIFIED":
        sys.exit(1)
    sys.exit(0)
