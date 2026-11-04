"""Story Change Analyst — diffs a proposed use against confirmed choices."""
from __future__ import annotations

import uuid
from typing import Any

from app.agents._common import make_output, split_findings
from app.agents.base import BaseAgent


class StoryChangeAnalystAgent(BaseAgent):
    name = "story_change_analyst"
    prompt_version = "1.0.0"

    def build_system_prompt(self, context: dict[str, Any]) -> str:
        return (
            "You are the Story Change Analyst for SceneSteward. Compare the proposed use against the "
            "LATEST CONFIRMED participant choices only. Identify matching categories, missing categories, "
            "changed context, new platform/audience/territory, and anything requiring human review. "
            "Never treat silence as agreement; never approve a use."
        )

    def build_user_prompt(self, context: dict[str, Any], run_id: uuid.UUID) -> str:
        return f"run_id: {run_id}\nproject_id: {context['project_id']}\nContext JSON:\n{context}"

    def offline_result(self, context: dict[str, Any], run_id: uuid.UUID) -> dict[str, Any]:
        analysis_findings = context.get("analysis_findings", [])
        buckets = split_findings(analysis_findings)
        outcome = context.get("analysis_outcome") or "UNRESOLVED"

        findings: list[dict] = []
        for item in buckets["agreed"]:
            findings.append({**item, "finding": f"Aligned with confirmed choice: {item['finding']}"})
        for item in buckets["unsettled"]:
            findings.append({**item, "finding": f"Missing or unsettled permission: {item['finding']}"})
        for item in buckets["declined"]:
            findings.append({**item, "finding": f"Conflict with explicit refusal: {item['finding']}"})
        for item in buckets["conflict"]:
            findings.append({**item, "finding": f"Conflicting records: {item['finding']}"})
        if not findings:
            findings.append({
                "category": None,
                "finding": "No categories could be matched to this proposed use.",
                "choice": None, "source_references": [],
                "confidence": "low",
                "uncertainty": "Use parameters did not map to any known consent category",
            })

        use = context.get("proposed_use", {})
        changed_signals = [k for k in ("platform", "audience", "territory", "purpose") if use.get(k)]
        recommended = [
            "Human review is required before any production step relying on the missing categories.",
            "Discuss the following with the participant: " + ", ".join(
                sorted({f["category"] for f in buckets["unsettled"] if f.get("category")}) or ["all unmatched categories"]
            ),
        ]
        if buckets["declined"]:
            recommended.insert(0, "HALT: the participant declined at least one implicated category.")
        if changed_signals:
            recommended.append(f"Changed context detected across: {', '.join(changed_signals)} — verify each was covered by the recorded choices.")

        return make_output(context=context, run_id=run_id, agent=self.name, result=outcome,
                           findings=findings, recommended_actions=recommended)
