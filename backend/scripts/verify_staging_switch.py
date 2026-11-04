"""Verification harness for Live Staging Switch (Agent Switch) Integration.

Tests:
1. Base URL health check
2. Agent authentication and ops discovery
3. Connection verification status
"""
from __future__ import annotations

import sys

from app.core.config import get_settings
from app.integrations.switch.http_adapter import HttpSwitchAdapter


def verify_switch_adapter() -> dict[str, str | bool]:
    settings = get_settings()
    results: dict[str, str | bool] = {
        "adapter": settings.switch_adapter,
        "base_url": settings.switch_base_url or "<unconfigured>",
        "agent_id": settings.switch_agent_id or "<unconfigured>",
        "status": "BLOCKED",
    }

    print("=" * 60)
    print("SceneSteward — Staging Switch Integration Verification")
    print("=" * 60)
    print(f"Switch Adapter: {settings.switch_adapter}")
    print(f"Switch Base URL: {settings.switch_base_url or '<unconfigured>'}")
    print(f"Switch Agent ID: {settings.switch_agent_id or '<unconfigured>'}")
    print(f"Switch API Key: {'YES (present)' if bool(settings.switch_api_key) else 'NO (missing)'}")

    if settings.switch_adapter != "http" or not settings.switch_base_url or not settings.switch_api_key or not settings.switch_agent_id:
        print("\n[RESULT] BLOCKED: SWITCH_ADAPTER is not 'http' or credentials are missing.")
        results["detail"] = "SWITCH_ADAPTER != http or SWITCH_BASE_URL/SWITCH_API_KEY/SWITCH_AGENT_ID missing"
        return results

    try:
        adapter = HttpSwitchAdapter()
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] Failed to instantiate HttpSwitchAdapter: {exc}")
        results["detail"] = str(exc)
        return results

    print("\n[1/1] Calling verify_connection() on Switch host ...")
    try:
        status_result = adapter.verify_connection()
        print(f"Connection Status: {status_result.status}")
        print(f"Details: {status_result.detail}")

        if status_result.status == "configured_verified":
            results["status"] = "LIVE_VERIFIED"
            print("\n>>> SWITCH STATUS: LIVE_VERIFIED <<<")
        else:
            results["status"] = "BLOCKED"
            results["detail"] = f"Status returned: {status_result.status} ({status_result.detail})"
            print(f"\n>>> SWITCH STATUS: BLOCKED ({status_result.status}) <<<")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Verification failed: {exc}")
        results["detail"] = str(exc)

    return results


if __name__ == "__main__":
    res = verify_switch_adapter()
    if res["status"] != "LIVE_VERIFIED":
        sys.exit(1)
    sys.exit(0)
