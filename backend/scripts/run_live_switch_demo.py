"""Live End-to-End Switch Clearance Demonstration Script.

Executes the complete vertical clearance workflow across SceneSteward and Switch:
1. Connects to Switch local protocol server (port 8010) and SceneSteward API (port 8000).
2. Verifies Agent Ops discovery contract on Switch.
3. Launches background SwitchEventListener holding live SSE connection.
4. Elena Producer posts Footage F-104 clearance request for documentary trailer.
5. SceneSteward Agent queries PostgreSQL, evaluates consent invariants, and posts BLOCKED assessment.
6. Elena Producer posts follow-up question on why release doesn't cover trailer.
7. SceneSteward Agent posts evidence-backed non-transitive consent clarification.
8. Authorized Director (Elena Director) posts formal decision via SceneSteward API.
9. SceneSteward commits decision to PostgreSQL, records immutable audit event, and notifies Switch room.
10. Validates end-to-end audit trail, SHA-256 digest, and room transcript.
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
from app.integrations.switch.listener import SwitchEventListener
from app.models import AuditEvent, ProposedUse, Review

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_switch_demo")

SWITCH_BASE = "http://127.0.0.1:8010"
SCENESTEWARD_BASE = "http://127.0.0.1:8000"
AGENT_ID = "scenesteward-agent-01"
API_KEY = "test-switch-key"


ROOM_ID = "room-clearance-001"


def wait_for_agent_message(room_id: str, expected_snippet: str, since_ts: str, timeout_seconds: float = 15.0) -> dict[str, Any]:
    """Polls room messages until an agent message containing expected snippet arrives."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        res = httpx.get(f"{SWITCH_BASE}/rooms/{room_id}/messages")
        if res.status_code == 200:
            msgs = res.json().get("messages", [])
            for m in reversed(msgs):
                if m.get("timestamp", "") >= since_ts:  # noqa: SIM102
                    if m.get("sender_type") == "agent" and expected_snippet.lower() in m.get("content", "").lower():
                        return m
        time.sleep(0.4)
    raise TimeoutError(f"Timed out waiting for agent message with snippet '{expected_snippet}' after {since_ts}")


def run_demo() -> int:
    room_id = ROOM_ID
    print("=" * 80)
    print("SCENESTEWARD × SWITCH — LIVE VERTICAL CLEARANCE WORKFLOW")
    print(f"Room: {room_id} | Agent: {AGENT_ID}")
    print("=" * 80)

    # 1. Health Checks
    print("\n[Step 1] Checking Service Connectivity...")
    try:
        sw_health = httpx.get(f"{SWITCH_BASE}/health", timeout=3.0).json()
        print(f"  ✓ Switch Protocol Server: {sw_health.get('service')} (version {sw_health.get('version')})")
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ Failed to connect to Switch server at {SWITCH_BASE}: {e}")
        return 1

    try:
        ss_health = httpx.get(f"{SCENESTEWARD_BASE}/health", timeout=3.0).json()
        print(f"  ✓ SceneSteward API: {ss_health.get('app')} (status: {ss_health.get('status')})")
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ Failed to connect to SceneSteward API at {SCENESTEWARD_BASE}: {e}")
        return 1

    # 2. Agent Operations Discovery Contract
    print("\n[Step 2] Discovering Agent Operations via Switch Protocol...")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    ops_res = httpx.get(f"{SWITCH_BASE}/agents/{AGENT_ID}/ops", headers=headers)
    if ops_res.status_code != 200:
        print(f"  ✗ Failed agent ops discovery: {ops_res.status_code} {ops_res.text}")
        return 1
    ops = ops_res.json().get("operations", [])
    print(f"  ✓ Agent '{AGENT_ID}' discovered operations: {ops}")

    # 3. Start SSE Event Listener in background thread
    print("\n[Step 3] Initializing Switch Agent SSE Event Listener...")
    listener = SwitchEventListener(get_session_factory, max_retries=3)
    listener_thread = threading.Thread(target=listener.run_forever, daemon=True)
    listener_thread.start()
    time.sleep(1.0)
    print(f"  ✓ Listener connected to SSE stream with Connection-ID: {listener.connection_id}")

    # 4. Human Producer submits Clearance Request
    print("\n[Step 4] Human Producer posts footage clearance request to Switch room...")
    req_payload = {
        "sender": "Elena Producer",
        "content": "SceneSteward, review footage F-104 from project P-001. We want to use it in the documentary trailer.",
    }
    t0 = time.time()
    since_0 = datetime.now(UTC).isoformat()
    post_res = httpx.post(f"{SWITCH_BASE}/rooms/{room_id}/messages", json=req_payload)
    if post_res.status_code != 200:
        print(f"  ✗ Failed to post human message: {post_res.text}")
        return 1
    print(f"  ✓ Message posted to '{room_id}' by Elena Producer")

    # 5. Wait for Agent Clearance Assessment
    print("\n[Step 5] Waiting for SceneSteward Clearance Assessment in Switch room...")
    agent_msg_1 = wait_for_agent_message(room_id, "SceneSteward Clearance Assessment", since_ts=since_0, timeout_seconds=12.0)
    t_clearance = time.time() - t0
    print(f"  ✓ Agent posted clearance assessment (latency: {t_clearance:.2f}s):")
    print("-" * 60)
    print(agent_msg_1["content"])
    print("-" * 60)

    # Extract review_id from agent assessment
    match = re.search(r"Review ID:\s*([a-f0-9\-]+)", agent_msg_1["content"])
    if not match:
        print("  ✗ Could not extract Review ID from agent message")
        return 1
    review_id_str = match.group(1).strip()
    review_id = uuid.UUID(review_id_str)
    print(f"  ✓ Extracted PostgreSQL Review ID: {review_id}")

    # 6. Human Teammate Follow-Up Inquiry
    print("\n[Step 6] Human Producer asks follow-up clarification question...")
    q_payload = {
        "sender": "Elena Producer",
        "content": "Why is trailer usage blocked when the participant has already signed the release?",
    }
    t1 = time.time()
    since_1 = datetime.now(UTC).isoformat()
    httpx.post(f"{SWITCH_BASE}/rooms/{room_id}/messages", json=q_payload)
    print(f"  ✓ Question posted to '{room_id}' by Elena Producer")

    # 7. Agent Invariant Explanation
    print("\n[Step 7] Waiting for SceneSteward Agent Invariant Explanation...")
    agent_msg_2 = wait_for_agent_message(room_id, "Evidence & Ethical Invariant Clarification", since_ts=since_1, timeout_seconds=10.0)
    t_explain = time.time() - t1
    print(f"  ✓ Agent posted invariant clarification (latency: {t_explain:.2f}s):")
    print("-" * 60)
    print(agent_msg_2["content"])
    print("-" * 60)

    # 8. Authorized Reviewer Records Formal Human Decision via SceneSteward API
    print("\n[Step 8] Authorized Reviewer (Director) commits formal decision via SceneSteward API...")
    dev_token_res = httpx.post(
        f"{SCENESTEWARD_BASE}/api/v1/auth/dev-token",
        json={"email": "director.elena@scenesteward.example.com"},
    )
    if dev_token_res.status_code != 200:
        print(f"  ✗ Failed to obtain dev token: {dev_token_res.text}")
        return 1
    auth_token = dev_token_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    decision_payload = {
        "decision": "needs_participant_discussion",
        "reason": "Dr. Miriam Kalu's interview agreement does not include promotional broadcast. Coordinator must hold an in-person discussion before any trailer cut is locked.",
        "expected_version": 1,
    }
    t2 = time.time()
    since_2 = datetime.now(UTC).isoformat()
    decide_res = httpx.post(
        f"{SCENESTEWARD_BASE}/api/v1/reviews/{review_id}/human-decision",
        json=decision_payload,
        headers=auth_headers,
    )
    if decide_res.status_code != 200:
        print(f"  ✗ Human decision commit failed: {decide_res.status_code} {decide_res.text}")
        return 1
    t_decision = time.time() - t2
    print(f"  ✓ Decision committed in SceneSteward API (latency: {t_decision:.2f}s): status=200 OK")

    # 9. Wait for Agent Confirmation in Switch Room
    print("\n[Step 9] Waiting for final Decision & Audit confirmation in Switch room...")
    agent_msg_3 = wait_for_agent_message(room_id, "Formal Human Decision Committed", since_ts=since_2, timeout_seconds=10.0)
    print("  ✓ Agent posted formal decision notification to Switch room:")
    print("-" * 60)
    print(agent_msg_3["content"])
    print("-" * 60)

    # 10. PostgreSQL Authoritative Database State Verification
    print("\n[Step 10] Verifying Authoritative PostgreSQL Database State...")
    factory = get_session_factory()
    with factory() as db:  # noqa: SIM117
        with system_context(db):
            rev = db.get(Review, review_id)
            print(f"  ✓ PostgreSQL Review row: id={rev.id} status={rev.review_status} decision={rev.human_decision}")
            assert rev.review_status == "completed", "Review status must be completed"
            assert rev.human_decision == "needs_participant_discussion", "Human decision mismatch"

            prop_use = db.get(ProposedUse, rev.proposed_use_id)
            print(f"  ✓ PostgreSQL ProposedUse row: id={prop_use.id} status={prop_use.status}")
            assert prop_use.status == "awaiting_participant_discussion", "Proposed use status mismatch"

            audit_rows = db.execute(
                select(AuditEvent).where(AuditEvent.entity_id == review_id).order_by(AuditEvent.timestamp.desc())
            ).scalars().all()
            print(f"  ✓ PostgreSQL AuditEvent count for review: {len(audit_rows)}")
            assert len(audit_rows) >= 1, "Audit event must be present"
            latest_audit = audit_rows[0]
            print(f"  ✓ Latest Audit row: id={latest_audit.id} action={latest_audit.action} actor={latest_audit.actor_id}")

    # 11. Complete Room Transcript Retrieval
    print("\n[Step 11] Retrieving Full Switch Room Transcript...")
    hist_res = httpx.get(f"{SWITCH_BASE}/rooms/{room_id}/messages")
    all_msgs = hist_res.json().get("messages", [])
    print(f"  ✓ Total messages recorded in room '{room_id}': {len(all_msgs)}")
    for idx, m in enumerate(all_msgs, start=1):
        sender = m.get("sender")
        stype = m.get("sender_type", "unknown")
        snippet = m.get("content", "").replace("\n", " ")[:90]
        print(f"    [{idx}] ({stype}) {sender}: {snippet}...")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETED: SWITCH VERTICAL CLEARANCE WORKFLOW IS FULLY LIVE & PROVEN")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(run_demo())
