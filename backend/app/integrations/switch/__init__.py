"""Switch adapter factory + status reporting (no secrets are ever returned)."""
from __future__ import annotations

import logging

from app.core.config import get_settings
from app.integrations.switch.base import SwitchAdapter, SwitchStatus
from app.integrations.switch.inmemory_adapter import InMemorySwitchAdapter

logger = logging.getLogger("scenesteward.switch")

_test_instance: InMemorySwitchAdapter | None = None


def get_switch_adapter() -> SwitchAdapter:
    s = get_settings()
    if s.switch_adapter == "http":
        from app.integrations.switch.http_adapter import HttpSwitchAdapter
        return HttpSwitchAdapter()
    global _test_instance
    if _test_instance is None:
        _test_instance = InMemorySwitchAdapter()
    return _test_instance


def switch_status() -> SwitchStatus:
    s = get_settings()
    if s.switch_adapter == "test":
        return SwitchStatus(status="configured_verified", detail="test adapter — live connection NOT verified")
    if not (s.switch_base_url and s.switch_api_key and s.switch_agent_id):
        return SwitchStatus(status="missing_credentials")
    return get_switch_adapter().verify_connection()
