"""Live End-to-End Multi-Agent Switch Clearance Demonstration.

Demonstrates genuine multi-agent collaboration across:
1. Human Producer & Director (Elena Producer, Elena Director)
2. SceneSteward Documentary Clearance Agent (PostgreSQL consent governance)
3. Google Antigravity ACP Agent (Live ACP subprocess via Agent Client Protocol)
4. Shared Switch Collaboration Room ('room-clearance-001')
5. PostgreSQL 18 Authoritative Database & Immutable Audit Ledger
"""
from __future__ import annotations

import logging
import re
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import get_session_factory, system_context
from app.integrations.antigravity.config import AntigravityConfig
from app.integrations.antigravity.switch_bridge import AntigravitySwitchBridge
from app.integrations.switch.listener import SwitchEventListener
from app.models import AuditEvent, ProposedUse, Review

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_multi_agent_demo")

SWITCH_BASE = "http://127.0.0.1:8010"
SCENESTEWARD_BASE = "http://127.0.0.1:8000"
ROOM_ID = "room-clearance-001"


def wait_for_room_message(
    room_id: str,
    *,
    expected_sender: str,
    expected_snippet: str,
    since_ts: str,
    timeout_seconds: float = 40.0,
) -> dict[str, Any]:
    """Polls room messages until a message from expected_sender containing expected_snippet arrives."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            res = httpx.get(f"{SWITCH_BASE}/rooms/{room_id}/messages", timeout=3.0)
            if res.status_code == 200:
                msgs = res.json().get("messages", [])
                for m in reversed(msgs):
                    if m.get("timestamp", "") >= since_ts:
                        sender_match = expected_sender.lower() in m.get("sender", "").lower()
                        snippet_match = expected_snippet.lower() in m.get("content", "").lower()
                        if sender_match and snippet_match:
                            return m
        except Exception:  # noqa: BLE001, S110
            pass
        time.sleep(0.5)
    raise TimeoutError(
        f"Timed out after {timeout_seconds}s waiting for message from '{expected_sender}' containing '{expected_snippet}'"
    )


def run_demo() -> int:
    print("=" * 80)
    print("SCENESTEWARD × SWITCH × GOOGLE ANTIGRAVITY")
    print("MISSION 43 — LIVE MULTI-AGENT COLLABORATION & ACP INTEGRATION")
    print("=" * 80)

    # 1. Connectivity Check
    print("\n[Step 1] Verifying System Services Connectivity...")
    try:
        sw_health = httpx.get(f"{SWITCH_BASE}/health", timeout=3.0).json()
        print(f"  ✓ Switch Platform: {sw_health.get('service')} (v{sw_health.get('version')})")
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ Switch server unavailable at {SWITCH_BASE}: {e}")
        return 1

    try:
        ss_health = httpx.get(f"{SCENESTEWARD_BASE}/health", timeout=3.0).json()
        print(f"  ✓ SceneSteward API: {ss_health.get('app')} (status: {ss_health.get('status')})")
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ SceneSteward API unavailable at {SCENESTEWARD_BASE}: {e}")
        return 1

    # 2. Initialize SceneSteward Agent Listener
    print("\n[Step 2] Initializing SceneSteward Agent Switch SSE Connection...")
    ss_listener = SwitchEventListener(get_session_factory, max_retries=3)
    ss_thread = threading.Thread(target=ss_listener.run_forever, daemon=True)
    ss_thread.start()
    time.sleep(1.0)
    print(f"  ✓ SceneSteward Agent connected to Switch room (Connection ID: {ss_listener.connection_id})")

    # 3. Launch and Connect Google Antigravity ACP Agent
    print("\n[Step 3] Initializing Google Antigravity ACP Agent Process...")
    agy_cfg = AntigravityConfig(
        enabled=True,
        executable_path="backend/tools/antigravity/agy_acp_server.exe",
        switch_base_url=SWITCH_BASE,
        startup_timeout_seconds=35.0,
        request_timeout_seconds=60.0,
    )
    agy_bridge = AntigravitySwitchBridge(config=agy_cfg)
    t_acp_start = time.time()
    ok = agy_bridge.start()
    if not ok:
        print("  ✗ Failed to initialize Google Antigravity ACP bridge")
        return 1
    t_acp_dur = time.time() - t_acp_start
    print(f"  ✓ Google Antigravity ACP Agent connected in {t_acp_dur:.2f}s:")
    print("    • ACP Protocol: JSON-RPC 2.0 (protocolVersion: 1)")
    print(f"    • Agent Info: {agy_bridge.acp_client.agent_info.get('title')} v{agy_bridge.acp_client.agent_info.get('version')}")
    print(f"    • ACP Session ID: {agy_bridge.acp_client.session_id}")
    print(f"    • Switch Bridge Connection ID: {agy_bridge.connection_id}")
    time.sleep(2.0)

    try:
        # 4. Human Producer Submits Footage Clearance Request
        print("\n[Step 4] Human Producer posts footage clearance request to Switch room...")
        req_payload = {
            "sender": "Elena Producer",
            "content": (
                "SceneSteward and Antigravity: We need to use footage F-104 from project P-001 in the documentary trailer. "
                "Please review the participant consent implications and technical architecture."
            ),
        }
        since_0 = datetime.now(UTC).isoformat()
        t0 = time.time()
        post_res = httpx.post(f"{SWITCH_BASE}/rooms/{ROOM_ID}/messages", json=req_payload)
        if post_res.status_code != 200:
            print(f"  ✗ Failed to post human message: {post_res.text}")
            return 1
        print(f"  ✓ Request posted to '{ROOM_ID}' by Elena Producer")

        # 5. SceneSteward Agent Responds with Ethical Clearance Assessment
        print("\n[Step 5] Waiting for SceneSteward Agent Clearance Assessment...")
        ss_msg_1 = wait_for_room_message(
            ROOM_ID,
            expected_sender="SceneSteward",
            expected_snippet="SceneSteward Clearance Assessment",
            since_ts=since_0,
            timeout_seconds=20.0,
        )
        t_ss = time.time() - t0
        print(f"  ✓ SceneSteward Agent posted ethical assessment in {t_ss:.2f}s:")
        print("-" * 65)
        print(ss_msg_1["content"])
        print("-" * 65)

        # Extract review_id
        match = re.search(r"Review ID:\s*([a-f0-9\-]+)", ss_msg_1["content"])
        if not match:
            print("  ✗ Could not extract Review ID from SceneSteward message")
            return 1
        review_id = uuid.UUID(match.group(1).strip())
        print(f"  ✓ Extracted PostgreSQL Review ID: {review_id}")

        # 6. Google Antigravity ACP Agent Responds with Technical Evaluation
        print("\n[Step 6] Waiting for Google Antigravity ACP Agent Technical Evaluation...")
        agy_msg_1 = wait_for_room_message(
            ROOM_ID,
            expected_sender="Google Antigravity",
            expected_snippet="Systems Architecture",
            since_ts=since_0,
            timeout_seconds=45.0,
        )
        t_agy = time.time() - t0
        print(f"  ✓ Google Antigravity posted technical assessment in {t_agy:.2f}s:")
        print("-" * 65)
        print(agy_msg_1["content"])
        print("-" * 65)

        # 7. Human Follow-Up Question
        print("\n[Step 7] Human Producer asks follow-up question...")
        q_payload = {
            "sender": "Elena Producer",
            "content": "Why is trailer usage blocked when the participant already signed a release?",
        }
        since_1 = datetime.now(UTC).isoformat()
        t1 = time.time()
        httpx.post(f"{SWITCH_BASE}/rooms/{ROOM_ID}/messages", json=q_payload)
        print(f"  ✓ Question posted to '{ROOM_ID}' by Elena Producer")

        # 8. SceneSteward Invariant Clarification
        print("\n[Step 8] Waiting for SceneSteward Agent Invariant Clarification...")
        ss_msg_2 = wait_for_room_message(
            ROOM_ID,
            expected_sender="SceneSteward",
            expected_snippet="Evidence & Ethical Invariant Clarification",
            since_ts=since_1,
            timeout_seconds=20.0,
        )
        t_ss2 = time.time() - t1
        print(f"  ✓ SceneSteward Agent posted invariant clarification in {t_ss2:.2f}s:")
        print("-" * 65)
        print(ss_msg_2["content"])
        print("-" * 65)

        # 9. Authorized Reviewer Commits Decision via SceneSteward API
        print("\n[Step 9] Authorized Director (Elena Director) records decision via SceneSteward API...")
        dev_token_res = httpx.post(
            f"{SCENESTEWARD_BASE}/api/v1/auth/dev-token",
            json={"email": "director.elena@scenesteward.example.com"},
        )
        auth_token = dev_token_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {auth_token}"}

        decision_payload = {
            "decision": "needs_participant_discussion",
            "reason": (
                "Dr. Miriam Kalu's interview agreement does not include promotional broadcast. "
                "Coordinator must hold an in-person discussion before any trailer cut is locked."
            ),
            "expected_version": 1,
        }
        since_2 = datetime.now(UTC).isoformat()
        t2 = time.time()
        decide_res = httpx.post(
            f"{SCENESTEWARD_BASE}/api/v1/reviews/{review_id}/human-decision",
            json=decision_payload,
            headers=auth_headers,
        )
        if decide_res.status_code != 200:
            print(f"  ✗ Human decision commit failed: {decide_res.status_code} {decide_res.text}")
            return 1
        t_decision = time.time() - t2
        print(f"  ✓ Decision committed in SceneSteward API in {t_decision:.2f}s: status=200 OK")

        # 10. SceneSteward Agent Notifies Room with Decision & Audit Proof
        print("\n[Step 10] Waiting for Formal Human Decision Notification in Switch Room...")
        ss_msg_3 = wait_for_room_message(
            ROOM_ID,
            expected_sender="SceneSteward",
            expected_snippet="Formal Human Decision Committed",
            since_ts=since_2,
            timeout_seconds=20.0,
        )
        print("  ✓ Final decision & cryptographic audit proof posted to Switch room:")
        print("-" * 65)
        print(ss_msg_3["content"])
        print("-" * 65)

        # 11. Authoritative Database Verification
        print("\n[Step 11] Verifying Authoritative PostgreSQL Database State...")
        factory = get_session_factory()
        with factory() as db:  # noqa: SIM117
            with system_context(db):
                rev = db.get(Review, review_id)
                assert rev.review_status == "completed"
                assert rev.human_decision == "needs_participant_discussion"
                print(f"  ✓ Review row verified: id={rev.id} decision={rev.human_decision}")

                prop_use = db.get(ProposedUse, rev.proposed_use_id)
                assert prop_use.status == "awaiting_participant_discussion"
                print(f"  ✓ ProposedUse row verified: id={prop_use.id} status={prop_use.status}")

                audit_rows = (
                    db.execute(select(AuditEvent).where(AuditEvent.entity_id == review_id))
                    .scalars()
                    .all()
                )
                assert len(audit_rows) >= 1
                print(f"  ✓ AuditEvent row verified: count={len(audit_rows)} latest_action={audit_rows[-1].action}")

        # 12. Complete Switch Room Transcript
        print("\n[Step 12] Retrieving Complete Switch Room Transcript...")
        hist_res = httpx.get(f"{SWITCH_BASE}/rooms/{ROOM_ID}/messages")
        all_msgs = hist_res.json().get("messages", [])
        print(f"  ✓ Total messages recorded in room '{ROOM_ID}': {len(all_msgs)}")
        for idx, m in enumerate(all_msgs, start=1):
            sender = m.get("sender")
            stype = m.get("sender_type", "unknown")
            snippet = m.get("content", "").replace("\n", " ")[:85]
            print(f"    [{idx}] ({stype}) {sender}: {snippet}...")

        print("\n" + "=" * 80)
        print("MISSION 43 VERIFICATION SUCCESSFUL:")
        print("GOOGLE ANTIGRAVITY ACP + SCENESTEWARD AGENT + SWITCH + POSTGRESQL VERIFIED END-TO-END")
        print("=" * 80)
        return 0

    finally:
        agy_bridge.stop()


if __name__ == "__main__":
    sys.exit(run_demo())
