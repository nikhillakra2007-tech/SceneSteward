"""Configuration for Google Antigravity ACP integration."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


def get_default_executable_path() -> str:
    # This file lives at <repo>/backend/app/integrations/antigravity/config.py
    file_path = Path(__file__).resolve()
    backend_root = file_path.parents[3]          # <repo>/backend
    repo_root = file_path.parents[4]             # <repo>
    candidates = [
        backend_root / "tools" / "antigravity" / "agy_acp_server.exe",
        repo_root / "backend" / "tools" / "antigravity" / "agy_acp_server.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


class AntigravityConfig(BaseModel):
    enabled: bool = Field(default=True)
    executable_path: str = Field(default_factory=get_default_executable_path)
    startup_timeout_seconds: float = Field(default=30.0)
    request_timeout_seconds: float = Field(default=60.0)
    # Official ACP auth flow: initialize -> authenticate -> session/new.
    # "oauth-personal" is the interactive Google login; the ACP binary refreshes an
    # existing token silently, so this only needs a human when no token is present.
    auth_method: str = Field(default="oauth-personal")
    auth_timeout_seconds: float = Field(default=120.0)
    # Tool execution stays denied unless an operator opts in: the assessor only needs
    # to read the workspace, never to modify it.
    auto_approve_tools: bool = Field(default=False)
    workspace_root: str | None = Field(default=None)
    agent_id: str = Field(default="google-antigravity-01")
    agent_name: str = Field(default="Google Antigravity")
    switch_base_url: str = Field(default="http://127.0.0.1:8010")
    switch_api_key: str = Field(default="test-switch-key-antigravity")


_CONFIG: AntigravityConfig | None = None


def get_antigravity_config() -> AntigravityConfig:
    global _CONFIG
    if _CONFIG is None:
        enabled = os.getenv("ANTIGRAVITY_ENABLED", "true").lower() in ("1", "true", "yes")
        exe_path = os.getenv("ANTIGRAVITY_EXECUTABLE") or get_default_executable_path()
        base_url = os.getenv("SWITCH_BASE_URL", "http://127.0.0.1:8010")
        _CONFIG = AntigravityConfig(
            enabled=enabled,
            executable_path=exe_path,
            switch_base_url=base_url,
            auth_method=os.getenv("ANTIGRAVITY_AUTH_METHOD", "oauth-personal"),
            auto_approve_tools=os.getenv("ANTIGRAVITY_AUTO_APPROVE_TOOLS", "false").lower() in ("1", "true", "yes"),
            workspace_root=os.getenv("ANTIGRAVITY_WORKSPACE") or None,
        )
    return _CONFIG

