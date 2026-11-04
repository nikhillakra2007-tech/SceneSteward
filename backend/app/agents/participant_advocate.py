"""Participant Advocate — participant-centred concerns and questions to ask.

Never makes decisions for the participant; only surfaces concerns and proposes
questions for the humans who will talk with them.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.agents._common import make_output
from app.agents.base import BaseAgent


class ParticipantAdvocateAgent(BaseAgent):
    name = "participant_advocate"
    prompt_version = "1.0.0"

    def build_system_prompt(self, context: dict[str, Any]) -> str:
        return (
            "You are the Participant Advocate for SceneSteward. Review the plan from the participant's "
            "perspective: accessibility, language, understandability, sensitive context, unanticipated reuse, "
            "communication needs. Suggest questions for the humans to ask the participant. "
            "Never answer for the participant; never override their recorded choices."
        )

    def build_user_prompt(self, context: dict[str, Any], run_id: uuid.UUID) -> str:
        return f"run_id: {run_id}\nproject_id: {context['project_id']}\nContext JSON:\n{context}"

    def offline_result(self, context: dict[str, Any], run_id: uuid.UUID) -> dict[str, Any]:
        private = context.get("participant_private", {}) or {}
        findings: list[dict] = []
        questions: list[str] = []

        accessibility = private.get("accessibility_requirements") or {}
        if accessibility:
            needs = ", ".join(sorted(accessibility)[:6]) if isinstance(accessibility, dict) else str(accessibility)[:200]
            findings.append({
                "category": "accessibility",
                "finding": f"Participant has recorded accessibility requirements: {needs}. Materials and review sessions must accommodate them.",
                "choice": None, "source_references": ["participant:accessibility_requirements"],
                "confidence": "high", "uncertainty": None,
            })
            questions.append(f"Would you like the review materials provided in a different format to support: {needs}?")

        language = private.get("preferred_language")
        if language:
            findings.append({
                "category": "language",
                "finding": f"Preferred language is '{language}'. Consent discussion should happen in that language or with a qualified interpreter.",
                "choice": None, "source_references": ["participant:preferred_language"],
                "confidence": "high", "uncertainty": None,
            })
            if language.lower() not in ("en", "eng", "english"):
                questions.append("Would you like the consent conversation in your preferred language, or with an interpreter present?")

        privacy = private.get("privacy_preferences") or {}
        if privacy:
            findings.append({
                "category": "privacy",
                "finding": f"Recorded privacy preferences: {list(privacy)[:6] if isinstance(privacy, dict) else privacy}. Any wider use must respect these.",
                "choice": None, "source_references": ["participant:privacy_preferences"],
                "confidence": "medium", "uncertainty": "Preferences need confirmation against this specific use",
            })
            questions.append("The planned use goes beyond what you may have expected — are you comfortable with it?")

        analysis = context.get("analysis_findings", [])
        missing = sorted({f.get("category") for f in analysis if f.get("choice") is None and f.get("category")})
        impact = sorted({f.get("category") for f in analysis if f.get("choice") == "agreed" and f.get("category")})
        if missing:
            findings.append({
                "category": "unanticipated_reuse",
                "finding": f"Proposed use is not covered by confirmed choices for: {', '.join(missing)}. Unease here is legitimate feedback, not an obstacle to manage.",
                "choice": None, "source_references": [],
                "confidence": "high", "uncertainty": None,
            })
            for cat in missing[:5]:
                questions.append(f"How do you feel about your participation being used in this way ({cat})? You can decline without giving a reason.")
        if impact:
            questions.append(f"You agreed to {', '.join(impact[:4])} earlier — does this new plan feel like the same thing, or something different?")

        if not findings:
            findings.append({
                "category": "general",
                "finding": "No participant-specific risk signals were detectable from the available context.",
                "choice": None, "source_references": [],
                "confidence": "low", "uncertainty": "Absence of signals is not proof of comfort",
            })
        questions.append("Is there anything about this plan that worries you, or anything you would like changed or left out?")

        return make_output(
            context=context, run_id=run_id, agent=self.name,
            result=context.get("analysis_outcome") or "NEEDS_DISCUSSION",
            findings=findings,
            recommended_actions=[f"Ask the participant: {q}" for q in questions[:10]],
        )
