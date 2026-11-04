"""Consent Analyst — extracts explicit choices and ambiguity from approved documents.

Never invents intention: statements without an explicit agreement/refusal verb are
reported as ambiguous; absence of a statement is reported as missing, never as agreed.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from app.agents._common import make_output
from app.agents.base import BaseAgent

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "interview_recording": ("interview",),
    "documentary_appearance": ("documentary", "appears in the film", "on camera", "appear on screen"),
    "name_identification": ("name",),
    "face_identification": ("face", "recognisable", "recognizable", "identifiable"),
    "sensitive_personal_details": ("sensitive", "personal details", "trauma", "health", "grief"),
    "promotional_clips": ("promo", "trailer", "marketing", "advert"),
    "festival_submissions": ("festival",),
    "ai_transcription": ("transcription", "transcribe"),
    "voice_cloning": ("voice clon", "voice reconstruct", "synthetic voice", "ai voice"),
    "synthetic_likeness": ("synthetic likeness", "deepfake", "face swap", "altered likeness"),
    "third_party_ai_processing": ("third-party ai", "third party ai", "ai vendor", "external ai"),
    "new_audience": ("wider audience", "general release", "new audience"),
    "new_territory": ("worldwide", "international", "new territory"),
    "new_platform": ("youtube", "tiktok", "instagram", "streaming", "social media", "podcast"),
    "new_story_context": ("out of context", "re-edit", "reframe", "new context"),
}

_AGREE = re.compile(r"\b(agree[sd]?|consent(?:ed)?|approve[sd]?|willing|happy to|okay with|ok with)\b", re.IGNORECASE)
_DECLINE = re.compile(r"\b(do not consent|decline[sd]?|refus\w*|not comfortable|unwilling|never authori[sz]e)\b", re.IGNORECASE)
_AMBIG = re.compile(r"\b(maybe|perhaps|not sure|possibly|might|depends|unclear)\b", re.IGNORECASE)


class ConsentAnalystAgent(BaseAgent):
    name = "consent_analyst"
    prompt_version = "1.0.0"

    def build_system_prompt(self, context: dict[str, Any]) -> str:
        return (
            "You are the Consent Analyst for SceneSteward, a participant-centred documentary workspace. "
            "Extract EXPLICIT participant choices from the provided material only. "
            "Never invent intention. Absence of evidence is 'not_discussed', never 'agreed'. "
            "Quote exact source references (document page or consent record id). Flag ambiguity and conflicts."
        )

    def build_user_prompt(self, context: dict[str, Any], run_id: uuid.UUID) -> str:
        return (
            f"run_id: {run_id}\nproject_id: {context['project_id']}\n"
            f"Analyse the material in this JSON context:\n{context}"
        )

    def offline_result(self, context: dict[str, Any], run_id: uuid.UUID) -> dict[str, Any]:
        findings: list[dict] = []
        documents = context.get("document_text") or []

        if documents:
            found: dict[str, str] = {}
            for page in documents:
                text = page["content"]
                ref = f"document_page:{page['page_number']}"
                # Split into sentence-ish chunks for scoped matching.
                for chunk in re.split(r"(?<=[.!?\n])\s+", text):
                    if not chunk.strip():
                        continue
                    low = chunk.lower()
                    sign = None
                    if _DECLINE.search(chunk):
                        sign = "declined"
                    elif _AGREE.search(chunk):
                        sign = "agreed"
                    elif _AMBIG.search(chunk):
                        sign = "needs_clarification"
                    if not sign:
                        continue
                    for category, keys in _CATEGORY_KEYWORDS.items():
                        if any(k in low for k in keys):
                            found.setdefault(category, sign if sign != "needs_clarification" else "needs_clarification")
                            findings.append({
                                "category": category,
                                "finding": f"Explicit statement detected ({sign}): \"{chunk.strip()[:220]}\"",
                                "choice": sign if sign != "needs_clarification" else None,
                                "source_references": [ref],
                                "confidence": "medium",
                                "uncertainty": "Regex-classified offline extraction; requires human review",
                            })
            if not found:
                findings.append({
                    "category": None,
                    "finding": "No explicit participant choice statements were detected in the document text.",
                    "choice": None,
                    "source_references": [f"document_page:{p['page_number']}" for p in documents],
                    "confidence": "high",
                    "uncertainty": "Extraction found no agreement or refusal language",
                })
            missing = [c for c in _CATEGORY_KEYWORDS if c not in found]
            declined = [c for c, s in found.items() if s == "declined"]
            if declined:
                result = "PARTICIPANT_DECLINED"
            elif missing:
                result = "NEEDS_DISCUSSION"
            else:
                result = "RECORDED_CHOICE_MATCH"
            recommended = ["Human must confirm each extracted statement before treating it as a participant decision."]
            if declined:
                recommended.append("Do not proceed with declined categories; record the refusal and discuss alternatives with the participant.")
            recommended += [f"Category with no explicit statement: {c} — ask the participant directly." for c in missing[:6]]
            return make_output(context=context, run_id=run_id, agent=self.name, result=result,
                               findings=findings, recommended_actions=recommended)

        # No document: summarise the confirmed record + engine analysis, if present.
        choices = context.get("latest_confirmed_choices", [])
        analysis = context.get("analysis_findings", [])
        outcome = context.get("analysis_outcome") or "UNRESOLVED"
        if not choices:
            findings.append({
                "category": None,
                "finding": "No confirmed consent record exists for this participant.",
                "choice": None,
                "source_references": [],
                "confidence": "high",
                "uncertainty": "Nothing has been recorded or confirmed",
            })
        else:
            for c in choices:
                findings.append({
                    "category": c["category"],
                    "finding": f"Confirmed record shows '{c['choice']}'.",
                    "choice": c["choice"],
                    "source_references": [r for r in [c.get("evidence_reference")] if r],
                    "confidence": "high",
                    "uncertainty": None if c["choice"] == "agreed" else "Not an agreement",
                })
        return make_output(
            context=context, run_id=run_id, agent=self.name, result=outcome,
            findings=findings,
            recommended_actions=["Verify the confirmed record with the participant before relying on it."] + [
                f"Unresolved: {f['category']}" for f in analysis if f.get("choice") is None
            ][:6],
        )
