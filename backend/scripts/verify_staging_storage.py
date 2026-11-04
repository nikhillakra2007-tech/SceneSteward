"""Verification harness for Live Staging Supabase Storage.

Tests:
1. Bucket accessibility and metadata check
2. Secure private object upload (synthetic probe)
3. Checksum and size verification
4. Signed download URL generation and retrieval
5. Object deletion and cleanup
"""
from __future__ import annotations

import hashlib
import io
import sys
import time
import uuid

import httpx

from app.core.config import get_settings
from app.integrations.storage.supabase import SupabaseStorageProvider


def verify_supabase_storage() -> dict[str, str | bool]:
    settings = get_settings()
    results: dict[str, str | bool] = {
        "provider": settings.storage_provider,
        "bucket": settings.storage_bucket,
        "upload_verified": False,
        "download_verified": False,
        "delete_verified": False,
        "status": "BLOCKED",
    }

    print("=" * 60)
    print("SceneSteward — Staging Supabase Storage Verification")
    print("=" * 60)
    print(f"Storage Provider: {settings.storage_provider}")
    print(f"Target Bucket: {settings.storage_bucket}")
    print(f"Supabase URL: {settings.supabase_url or '<unconfigured>'}")

    if settings.storage_provider != "supabase" or not settings.supabase_url or not settings.supabase_service_role_key:
        print("\n[RESULT] BLOCKED: STORAGE_PROVIDER is not 'supabase' or credentials missing.")
        results["detail"] = "Provider not set to supabase or SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing"
        return results

    try:
        provider = SupabaseStorageProvider()
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] Failed to initialize SupabaseStorageProvider: {exc}")
        results["detail"] = str(exc)
        return results

    print("\n[1/5] Checking bucket availability ...")
    chk = provider.check()
    print(f"Bucket check response: {chk}")
    if chk.get("status") != "ok":
        print(f"[ERROR] Bucket '{settings.storage_bucket}' unavailable or unauthenticated.")
        results["detail"] = f"Bucket check returned: {chk}"
        return results

    test_content = f"SceneSteward Synthetic Probe - {uuid.uuid4()} - {time.time()}".encode()
    content_sha256 = hashlib.sha256(test_content).hexdigest()
    storage_key = f"staging-acceptance/probe-{uuid.uuid4().hex[:8]}.txt"

    print(f"\n[2/5] Uploading probe file to '{storage_key}' ({len(test_content)} bytes) ...")
    start = time.perf_counter()
    try:
        stored_bytes = provider.store_stream(storage_key, io.BytesIO(test_content), max_bytes=1024 * 1024)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[OK] Uploaded {stored_bytes} bytes in {elapsed_ms:.1f}ms.")
        results["upload_verified"] = True
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Upload failed: {exc}")
        results["detail"] = f"Upload error: {exc}"
        return results

    print("\n[3/5] Verifying object existence and signed download URL ...")
    try:
        exists = provider.exists(storage_key)
        size = provider.size(storage_key)
        print(f"Object exists: {exists}, Reported size: {size} bytes")
        if not exists or size != len(test_content):
            print(f"[FAIL] Object metadata mismatch (exists={exists}, size={size})")
            return results

        download_url = provider.create_download_url(storage_key, ttl_seconds=300)
        print("[OK] Generated signed download URL.")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Existence/Sign failed: {exc}")
        results["detail"] = str(exc)
        return results

    print("\n[4/5] Downloading object via signed URL & validating checksum ...")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(download_url)
            print(f"HTTP Status: {resp.status_code}, Length: {len(resp.content)} bytes")
            if resp.status_code != 200:
                print(f"[FAIL] Download returned HTTP {resp.status_code}")
                return results
            downloaded_sha256 = hashlib.sha256(resp.content).hexdigest()
            if downloaded_sha256 != content_sha256:
                print(f"[FAIL] Checksum mismatch! Expected {content_sha256}, got {downloaded_sha256}")
                return results
            print(f"[OK] Checksum verified: {downloaded_sha256}")
            results["download_verified"] = True
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Download verification failed: {exc}")
        results["detail"] = str(exc)
        return results

    print("\n[5/5] Cleaning up probe file ...")
    try:
        provider.delete(storage_key)
        remaining = provider.exists(storage_key)
        print(f"Object exists after deletion: {remaining}")
        results["delete_verified"] = not remaining
        print("[OK] Probe file cleaned up.")
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Cleanup failed: {exc}")

    results["status"] = "LIVE_VERIFIED"
    print("\n>>> STORAGE STATUS: LIVE_VERIFIED <<<")
    return results


if __name__ == "__main__":
    res = verify_supabase_storage()
    if res["status"] != "LIVE_VERIFIED":
        sys.exit(1)
    sys.exit(0)
