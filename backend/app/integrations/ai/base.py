"""AI provider interface — one call shape for every agent."""
from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    name: str

    def complete_json(self, *, system: str, user: str, max_tokens: int = 2000) -> str:
        """Return raw model text; callers parse and validate it."""
        ...
