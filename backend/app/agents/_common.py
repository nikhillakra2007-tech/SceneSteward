"""Shared helpers for offline (deterministic) agent implementations."""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any


def make_output(*, context: dict[str, Any], run_id: uuid.UUID, agent: str, result: str,
                findings: list[dict], recommended_actions: list[str],
                requires_human_review: bool = True) -> dict[str, Any]:
    return {
        "agent": agent,
        "run_id": str(run_id),
        "project_id": context["project_id"],
        "participant_id": context.get("participant_id"),
        "proposed_use_id": context.get("proposed_use_id"),
        "result": result,
        "findings": findings,
        "recommended_actions": recommended_actions,
        "requires_human_review": requires_human_review,
    }


def split_findings(findings: Iterable[dict]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {"declined": [], "unsettled": [], "agreed": [], "conflict": []}
    for f in findings:
        choice = f.get("choice")
        if choice == "declined":
            buckets["declined"].append(f)
        elif choice == "agreed":
            buckets["agreed"].append(f)
        elif choice is None and f.get("confidence") == "medium":
            buckets["conflict"].append(f)
        else:
            buckets["unsettled"].append(f)
    return buckets
