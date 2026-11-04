"""Anthropic Messages API provider (used only when AI_PROVIDER=anthropic).

The model is instructed to treat document content as untrusted data and to
return a single JSON object; the caller validates it against the agent output
schema and rejects anything else.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings
from app.core.exceptions import UpstreamUnavailable

logger = logging.getLogger("scenesteward.ai.anthropic")
_API = "https://api.anthropic.com/v1/messages"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        s = get_settings()
        if not s.anthropic_api_key:
            raise UpstreamUnavailable("AI_PROVIDER=anthropic but ANTHROPIC_API_KEY is not configured", code="ai_unconfigured")
        self._key = s.anthropic_api_key
        self._model = s.ai_model
        self._timeout = s.ai_timeout_seconds

    @property
    def model_version(self) -> str:
        return self._model

    def complete_json(self, *, system: str, user: str, max_tokens: int = 2000) -> str:
        headers = {
            "x-api-key": self._key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        try:
            resp = httpx.post(_API, headers=headers, json=payload, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise UpstreamUnavailable("AI provider timed out", code="ai_timeout") from exc
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable("AI provider request failed", code="ai_unavailable") from exc
        if resp.status_code in (401, 403):
            raise UpstreamUnavailable("AI provider authentication failed", code="ai_failed_authentication")
        if resp.status_code == 429:
            raise UpstreamUnavailable("AI provider rate limit exceeded", code="ai_rate_limited")
        if resp.status_code >= 400:
            logger.warning("anthropic error status=%s", resp.status_code)
            raise UpstreamUnavailable("AI provider returned an error", code="ai_error")
        data = resp.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        return "".join(parts)
