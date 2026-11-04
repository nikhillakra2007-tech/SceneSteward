"""Production Coordinator — turns findings into human-owned work.

Never sends anything to a participant; produces drafts and task suggestions only.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.agents._common import make_output
from app.agents.base import BaseAgent


class ProductionCoordinatorAgent(BaseAgent):
    name = "production_coordinator"
    prompt_version = "1.0.0"

    def build_system_prompt(self, context: dict[str, Any]) -> str:
        return (
            "You are the Production Coordinator for SceneSteward. Convert the validated findings into "
            "human-owned tasks, review summaries, and DRAFT participant communications. "
            "You never send communications, never approve uses, and never mark consent as confirmed. "
            "Propose deadlines realistically and flag every unresolved issue."
        )

    def build_user_prompt(self, context: dict[str, Any], run_id: uuid.UUID) -> str:
        return f"run_id: {run_id}\nproject_id: {context['project_id']}\nContext JSON:\n{context}"

    def offline_result(self, context: dict[str, Any], run_id: uuid.UUID) -> dict[str, Any]:
        actions: list[str] = []
        findings: list[dict] = []
        analysis = context.get("analysis_findings", [])
        outcome = context.get("analysis_outcome") or "NEEDS_DISCUSSION"
        missing = sorted({f.get("category") for f in analysis if f.get("choice") is None and f.get("category")})
        declined = sorted({f.get("category") for f in analysis if f.get("choice") == "declined" and f.get("category")})

        for cat in declined:
            actions.append(f"STOP workstream touching '{cat}'; record refusal; brief the participant on alternatives (do not persuade).")
        for cat in missing:
            actions.append(f"Schedule a participant discussion for '{cat}' and record the outcome as a NEW consent version.")
        if outcome == "HUMAN_REVIEW_REQUIRED":
            actions.append("Reconcile conflicting confirmed records with the participant before any scheduling or spend.")
        actions.append("Human reviewer must record the formal decision in SceneSteward; Switch/chat output is never a decision.")
        actions.append("Draft (not send) a participant conversation outline covering: what changes, why, and the right to decline.")

        if missing:
            findings.append({
                "category": "coordination",
                "finding": f"Follow-up discussion required for: {', '.join(missing)}.",
                "choice": None, "source_references": [],
                "confidence": "high", "uncertainty": None,
            })
        if declined:
            findings.append({
                "category": "coordination",
                "finding": f"Refused categories must be removed from the plan: {', '.join(declined)}.",
                "choice": None, "source_references": [],
                "confidence": "high", "uncertainty": None,
            })
        if not findings:
            findings.append({
                "category": "coordination",
                "finding": "No blocking items found; proceed to normal human review.",
                "choice": None, "source_references": [],
                "confidence": "medium", "uncertainty": "Normal review still applies",
            })

        return make_output(context=context, run_id=run_id, agent=self.name, result=outcome,
                           findings=findings, recommended_actions=actions)
