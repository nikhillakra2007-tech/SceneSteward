"""Tests for Google Antigravity ACP Client and protocol handling."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.integrations.antigravity.acp_client import ACPState, AntigravityACPClient
from app.integrations.antigravity.config import AntigravityConfig


def test_antigravity_config_resolution():
    cfg = AntigravityConfig()
    assert cfg.enabled is True
    assert cfg.agent_id == "google-antigravity-01"
    assert "agy_acp_server.exe" in cfg.executable_path


def test_acp_client_not_configured_when_disabled():
    cfg = AntigravityConfig(enabled=False)
    client = AntigravityACPClient(cfg)
    assert client.state == ACPState.NOT_CONFIGURED
    assert client.start() is False


def test_acp_client_missing_executable():
    cfg = AntigravityConfig(enabled=True, executable_path="non_existent_binary.exe")
    client = AntigravityACPClient(cfg)
    assert client.start() is False
    assert client.state == ACPState.ERROR


def test_acp_client_mock_handshake_and_session():
    cfg = AntigravityConfig(enabled=True, executable_path="dummy.exe")
    client = AntigravityACPClient(cfg)

    # Test initialization with simulated responses
    mock_init_resp = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": 1,
            "agentInfo": {"name": "antigravity-acp", "version": "1.4.5"},
            "agentCapabilities": {"loadSession": True},
        },
    }
    mock_auth_resp = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"_meta": {"tier": "pro"}},
    }
    mock_session_resp = {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {"sessionId": "test-session-uuid-123"},
    }
    mock_prompt_resp = {
        "jsonrpc": "2.0",
        "id": 4,
        "result": {"stopReason": "end_turn"},
    }

    with patch.object(client, "_send_request") as mock_send:
        mock_send.side_effect = [mock_init_resp, mock_auth_resp, mock_session_resp, mock_prompt_resp]
        with patch("subprocess.Popen"):
            # Simulate start
            client._state = ACPState.INITIALIZING
            resp = client._send_request({"id": 1})
            client._agent_info = resp["result"]["agentInfo"]
            client._state = ACPState.CONNECTED

            assert client.state == ACPState.CONNECTED
            assert client.agent_info["name"] == "antigravity-acp"

            # Create session
            sess_id = client.create_session("/tmp")
            assert sess_id == "test-session-uuid-123"
            assert client.state == ACPState.READY

            # Prompt
            def fake_send_request(req, timeout=60.0):
                if req.get("method") == "session/prompt":
                    client._active_prompt_chunks = ["Technical architecture assessment complete."]
                    return mock_prompt_resp
                return mock_send(req)

            with patch.object(client, "_send_request", side_effect=fake_send_request):
                reply = client.prompt("Analyze consent boundary")
                assert "Technical architecture" in reply
                assert client.state == ACPState.READY


@pytest.mark.skipif(
    not Path("backend/tools/antigravity/agy_acp_server.exe").exists(),
    reason="Official Antigravity ACP binary not present",
)
def test_real_antigravity_acp_binary_handshake():
    """Validates the genuine Google Antigravity ACP binary initialization."""
    cfg = AntigravityConfig(
        enabled=True,
        executable_path="backend/tools/antigravity/agy_acp_server.exe",
        startup_timeout_seconds=30.0,
    )
    client = AntigravityACPClient(cfg)
    try:
        ok = client.start()
        assert ok is True, f"Failed to start ACP binary: {client._last_error}"
        assert client.state == ACPState.CONNECTED
        assert client.agent_info.get("name") == "antigravity-acp"
        assert client.agent_info.get("version") == "1.4.5"
    finally:
        client.stop()
        assert client.state == ACPState.DISCONNECTED
