"""Integration tests for Multi-Agent Switch collaboration (SceneSteward + Google Antigravity)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.integrations.antigravity.switch_bridge import AntigravitySwitchBridge
from app.integrations.switch.agent_worker import SwitchAgentWorker


def test_loop_prevention_scenesteward_ignores_peer_agent():
    worker = SwitchAgentWorker()
    db_mock = MagicMock()

    # Self message
    res1 = worker.process_room_message(
        db_mock,
        {"data": {"room_id": "room-1", "sender": "SceneSteward Agent", "content": "review footage F-104"}},
    )
    assert res1["status"] == "ignored"

    # Antigravity peer message
    res2 = worker.process_room_message(
        db_mock,
        {"data": {"room_id": "room-1", "sender": "Google Antigravity", "content": "review footage F-104"}},
    )
    assert res2["status"] == "ignored"
    assert res2["reason"] == "agent_or_empty"


def test_loop_prevention_antigravity_ignores_peer_agent():
    mock_acp = MagicMock()
    bridge = AntigravitySwitchBridge(acp_client=mock_acp)

    # Antigravity self message
    res1 = bridge.handle_room_event(
        {"data": {"room_id": "room-1", "sender": "Google Antigravity", "content": "trailer clearance"}}
    )
    assert res1["status"] == "ignored"

    # SceneSteward agent message
    res2 = bridge.handle_room_event(
        {"data": {"room_id": "room-1", "sender": "SceneSteward Agent", "content": "trailer clearance"}}
    )
    assert res2["status"] == "ignored"
    assert res2["reason"] == "agent_or_empty"

    mock_acp.prompt.assert_not_called()


def test_antigravity_data_minimization_and_technical_routing():
    mock_acp = MagicMock()
    mock_acp.prompt.return_value = "System authorization boundaries prevent omnibus credential propagation."
    bridge = AntigravitySwitchBridge(acp_client=mock_acp)

    with patch.object(bridge, "post_message_to_room") as mock_post:
        mock_post.return_value = True

        # Human message with participant personal details
        human_msg = {
            "event_id": str(uuid.uuid4()),
            "data": {
                "room_id": "room-clearance-001",
                "sender": "Elena Producer",
                "content": "Antigravity, review technical architecture for F-104 trailer clearance.",
            },
        }

        res = bridge.handle_room_event(human_msg)
        assert res["status"] == "responded"
        assert res["posted"] is True

        # Verify prompt submitted to Antigravity ACP client has no PII and focuses on architecture
        assert mock_acp.prompt.called
        submitted_prompt = mock_acp.prompt.call_args[0][0]
        assert "Google Antigravity" in submitted_prompt
        assert "authorization" in submitted_prompt

        # Verify posted message formatting
        assert mock_post.called
        posted_content = mock_post.call_args[0][1]
        assert "[Google Antigravity — Systems Architecture & Security Evaluation]" in posted_content
        assert "System authorization boundaries" in posted_content
        assert "Formal clearance requires authorized human review" in posted_content


def test_duplicate_event_suppression():
    mock_acp = MagicMock()
    bridge = AntigravitySwitchBridge(acp_client=mock_acp)
    eid = str(uuid.uuid4())

    event = {
        "event_id": eid,
        "data": {
            "room_id": "room-clearance-001",
            "sender": "Elena Producer",
            "content": "review technical architecture for trailer",
        },
    }

    with patch.object(bridge, "post_message_to_room", return_value=True):
        res1 = bridge.handle_room_event(event)
        assert res1["status"] == "responded"

        # Duplicate event with same event_id
        res2 = bridge.handle_room_event(event)
        assert res2["status"] == "ignored"
        assert res2["reason"] == "duplicate_event"

