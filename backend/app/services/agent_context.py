"""Build minimal, agent-specific context bundles (data minimisation).

Nothing here sends more than the agent needs. Contact details, encryption keys,
raw tokens, and unrelated participants are never included.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.models import ConsentRecord, ProposedUse, StoryElement


def _choices_payload(record: ConsentRecord | None) -> list[dict[str, Any]]:
    if record is None:
        return []
    return [
        {"category": c.category, "choice": c.choice,
         "evidence_reference": c.evidence_reference,
         "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None}
        for c in record.choices
    ]


def _history_payload(records: list[ConsentRecord]) -> list[dict[str, Any]]:
    return [
        {"version_number": r.version_number, "record_status": r.record_status,
         "recorded_choice_summary": {c.category: c.choice for c in r.choices}}
        for r in records
    ]


def build_context(
    *,
    agent_name: str,
    project_id: uuid.UUID,
    participant_id: uuid.UUID | None,
    proposed_use: ProposedUse | None,
    story_element: StoryElement | None,
    latest_confirmed: ConsentRecord | None,
    confirmed_history: list[ConsentRecord],
    analysis_findings: list[dict] | None,
    analysis_outcome: str | None,
    participant_private: dict | None = None,   # accessibility_requirements / preferred_language / privacy_preferences (advocate only)
    document_text: list[dict] | None = None,   # [{page_number, content}] (consent analyst only)
    agent_outputs: dict[str, Any] | None = None,  # ethics/coordinator only
    input_reference: str | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "project_id": str(project_id),
        "participant_id": str(participant_id) if participant_id else None,
        "proposed_use_id": str(proposed_use.id) if proposed_use else None,
        "input_reference": input_reference or (f"proposed_use:{proposed_use.id}" if proposed_use else None),
    }

    if proposed_use:
        context["proposed_use"] = {
            "use_type": proposed_use.use_type,
            "platform": proposed_use.platform,
            "audience": proposed_use.audience,
            "purpose": proposed_use.purpose,
            "territory": proposed_use.territory,
            "context_description": proposed_use.context_description,
            "status": proposed_use.status,
        }
    if story_element:
        context["story_element"] = {
            "title": story_element.title,
            "scene_reference": story_element.scene_reference,
            "sensitivity_level": story_element.sensitivity_level,
        }

    if agent_name in ("consent_analyst", "story_change_analyst", "ethics_reviewer"):
        context["latest_confirmed_choices"] = _choices_payload(latest_confirmed)
        context["latest_confirmed_version"] = latest_confirmed.version_number if latest_confirmed else None
        context["latest_confirmed_record_id"] = str(latest_confirmed.id) if latest_confirmed else None
        context["historical_decisions"] = _history_payload(confirmed_history)
        context["analysis_findings"] = analysis_findings or []
        context["analysis_outcome"] = analysis_outcome

    if agent_name == "consent_analyst" and document_text is not None:
        # Cap total document text sent to the model (~12k chars).
        remaining, pages = 12000, []
        for page in document_text:
            take = page["content"][:remaining]
            if not take:
                break
            pages.append({"page_number": page["page_number"], "content": take})
            remaining -= len(take)
        context["document_text"] = pages

    if agent_name == "participant_advocate":
        context["participant_private"] = participant_private or {}
        context["analysis_findings"] = analysis_findings or []

    if agent_name in ("ethics_reviewer", "production_coordinator"):
        context["agent_outputs"] = agent_outputs or {}
        context["analysis_findings"] = analysis_findings or []
        context["analysis_outcome"] = analysis_outcome

    return context
