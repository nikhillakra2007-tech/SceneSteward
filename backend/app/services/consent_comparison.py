"""Deterministic consent comparison engine (ENGINE_VERSION = 1.0.0).

Compares a proposed use with the LATEST CONFIRMED participant choices and
produces structured findings. AI agents may contribute analysis, but outcome
determination always happens here, server-side, from persisted evidence.

Outcome rules (first match wins):
  PARTICIPANT_DECLINED    — any relevant category is explicitly declined in the
                            latest confirmed record
  HUMAN_REVIEW_REQUIRED   — conflicting confirmed versions disagree on a
                            relevant category
  NEEDS_DISCUSSION        — at least one relevant category is missing,
                            unconfirmed, or ambiguous (not 'agreed')
  RECORDED_CHOICE_MATCH   — every relevant category is explicitly agreed
  UNRESOLVED              — no relevant categories can be determined from the
                            input (e.g. empty use_type and no context keywords)
A RECORDED_CHOICE_MATCH is never a publication approval — human review still
applies downstream.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ENGINE_VERSION = "1.0.0"

NOT_AGREED = {"not_discussed", "needs_clarification", "awaiting_confirmation", "explained"}

# Base categories triggered by the structured use_type field.
_USE_TYPE_MAP: dict[str, tuple[str, ...]] = {
    "interview_excerpt_promotion": ("promotional_clips", "interview_recording", "new_audience"),
    "promotional_trailer": ("promotional_clips",),
    "promotional_clip": ("promotional_clips",),
    "promo_clip": ("promotional_clips",),
    "festival_submission": ("festival_submissions", "new_audience", "new_territory"),
    "festival_entry": ("festival_submissions", "new_audience"),
    "voice_reconstruction": ("voice_cloning", "third_party_ai_processing"),
    "voice_cloning": ("voice_cloning",),
    "synthetic_likeness": ("synthetic_likeness",),
    "ai_transcription": ("ai_transcription", "third_party_ai_processing"),
    "third_party_ai": ("third_party_ai_processing",),
    "theatrical_release": ("new_audience", "new_territory", "new_platform"),
    "broadcast": ("new_audience", "new_platform", "new_territory"),
    "streaming_release": ("new_platform", "new_audience", "new_territory"),
    "social_campaign": ("promotional_clips", "new_platform", "new_audience"),
    "documentary_screening": ("documentary_appearance", "new_audience", "festival_submissions"),
    "interview": ("interview_recording",),
    "name_release": ("name_identification",),
}

# Keyword scan over free text (platform, audience, purpose, territory, context).
_KEYWORD_RULES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(p, re.IGNORECASE), c) for p, c in [
        (r"\b(trailer|promo|advert|marketing|campaign)\w*\b", "promotional_clips"),
        (r"\bfestival\w*\b", "festival_submissions"),
        (r"\bvoice[\s-]?(clon|reconstruct|synth|generat)\w*\b", "voice_cloning"),
        (r"\b(synthetic|deepfake|face[\s-]?swap|likeness alteration|ai[\s-]?generat\w* (voice|face|image))\w*\b", "synthetic_likeness"),
        (r"\b(transcri|speech[\s-]?to[\s-]?text)\w*\b", "ai_transcription"),
        (r"\b(third[\s-]?party ai|external ai|ai processing|ai vendor)\b", "third_party_ai_processing"),
        (r"\bname\b", "name_identification"),
        (r"\b(face|identifiable|recogni[sz]able)\w*\b", "face_identification"),
        (r"\bsensitive\b", "sensitive_personal_details"),
        (r"\b(interview|conversation)\w*\b", "interview_recording"),
        (r"\b(wider|general|larger|mass)\b.{0,30}\baudience\b|\bnew audience\b", "new_audience"),
        (r"\b(international|worldwide|global|europe|north america|territory|territories)\b", "new_territory"),
        (r"\b(youtube|tiktok|instagram|facebook|x\.com|twitter|streaming|netflix|vimeo|social media|podcast)\b", "new_platform"),
        (r"\b(re-?edit|reframe|recontextual|out of context|new context|additional context|montaged?)\b", "new_story_context"),
        (r"\b(documentary appearance|appears? in the film|on[\s-]?camera)\b", "documentary_appearance"),
    ]
)


@dataclass
class NormalizedUse:
    relevant_categories: list[str]
    matched_keywords: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    outcome: str
    findings: list[dict]
    matched_consent_record_ids: list[str]
    requires_human_review: bool = True


def normalize_proposed_use(use) -> NormalizedUse:
    relevant: set[str] = set()
    matched: dict[str, list[str]] = {}

    use_type_key = (use.use_type or "").strip().lower().replace(" ", "_").replace("-", "_")
    for cat in _USE_TYPE_MAP.get(use_type_key, ()):  # exact map first
        relevant.add(cat)
        matched.setdefault(cat, []).append(f"use_type:{use.use_type}")

    text_parts = [use.use_type or "", use.platform or "", use.audience or "", use.purpose or "",
                  use.territory or "", use.context_description or ""]
    blob = " \n ".join(text_parts).lower()
    for pattern, category in _KEYWORD_RULES:
        hits = [m.group(0) for m in pattern.finditer(blob)]
        if hits:
            relevant.add(category)
            matched.setdefault(category, []).extend(f"keyword:{h}" for h in hits[:3])

    # A sensitive excerpt used for anything promotional always needs sensitivity review.
    if "sensitive" in blob and ("promotional_clips" in relevant or "festival_submissions" in relevant):
        relevant.add("sensitive_personal_details")
        matched.setdefault("sensitive_personal_details", []).append("keyword:sensitive+promotion")

    return NormalizedUse(sorted(relevant), matched)


def _choice_index(record) -> dict[str, object]:
    return {c.category: c for c in record.choices}


def compare_with_confirmed_record(latest, history, normalized: NormalizedUse) -> ComparisonResult:
    findings: list[dict] = []
    if not normalized.relevant_categories:
        return ComparisonResult(
            outcome="UNRESOLVED",
            findings=[{
                "category": None,
                "finding": "Could not determine which consent categories apply to this proposed use.",
                "choice": None,
                "source_references": [],
                "confidence": "low",
                "uncertainty": "use_type and context provide no recognisable category signals",
            }],
            matched_consent_record_ids=[],
        )

    choices = _choice_index(latest) if latest else {}
    matched_ids = [str(r.id) for r in ([latest] if latest else [])] + [str(r.id) for r in history if latest is None or r.id != latest.id]

    declined: list[str] = []
    conflicts: list[str] = []
    unsettled: list[str] = []
    agreed: list[str] = []

    # Conflict detection across confirmed versions (defensive; supersession should prevent this).
    confirmed_chain = [r for r in ([latest] if latest else [])] + [r for r in history if (latest is None or r.id != latest.id)]
    by_version = sorted(confirmed_chain, key=lambda r: r.version_number)

    for category in normalized.relevant_categories:
        chain_choices = [next((c for c in r.choices if c.category == category), None) for r in by_version]
        recorded = [(r.version_number, c) for r, c in zip(by_version, chain_choices) if c is not None]
        distinct_agreements = {(c.choice) for _, c in recorded}
        if len(distinct_agreements) > 1 and any(c.choice == "agreed" for _, c in recorded) and any(c.choice == "declined" for _, c in recorded):
            conflicts.append(category)

        row = choices.get(category)
        if row is None:
            findings.append({
                "category": category,
                "finding": "No confirmed participant choice was found for this category.",
                "choice": None,
                "source_references": [],
                "confidence": "high",
                "uncertainty": "The available confirmed record does not address this use",
            })
            unsettled.append(category)
            continue
        ref = f"consent_record:{latest.id}#choice:{row.id}" if latest else None
        evidence = [e for e in [ref, row.evidence_reference] if e]
        if row.choice == "declined":
            declined.append(category)
            findings.append({
                "category": category,
                "finding": "The participant has EXPLICITLY DECLINED this category in the confirmed record.",
                "choice": "declined",
                "source_references": evidence,
                "confidence": "high",
                "uncertainty": None,
            })
        elif row.choice == "agreed":
            agreed.append(category)
            findings.append({
                "category": category,
                "finding": "The latest confirmed record shows explicit agreement for this category.",
                "choice": "agreed",
                "source_references": evidence,
                "confidence": "high",
                "uncertainty": None,
            })
        else:
            unsettled.append(category)
            label = {
                "not_discussed": "Not discussed with the participant",
                "needs_clarification": "Participant asked for clarification; no agreement recorded",
                "awaiting_confirmation": "Awaiting participant confirmation",
                "explained": "Explained to the participant; no agreement recorded",
            }.get(row.choice, row.choice)
            findings.append({
                "category": category,
                "finding": f"{label}. This is NOT agreement.",
                "choice": row.choice,
                "source_references": evidence,
                "confidence": "high",
                "uncertainty": "A recorded conversation exists but contains no consent for this use",
            })

    if declined:
        outcome = "PARTICIPANT_DECLINED"
    elif conflicts:
        outcome = "HUMAN_REVIEW_REQUIRED"
        for category in conflicts:
            findings.append({
                "category": category,
                "finding": "Confirmed versions disagree on this category; human review must reconcile them.",
                "choice": None,
                "source_references": [f"consent_record_versions:{','.join(str(r.version_number) for r in by_version)}"],
                "confidence": "medium",
                "uncertainty": "Deterministic reconciliation is not possible from the stored evidence",
            })
    elif unsettled:
        outcome = "NEEDS_DISCUSSION"
    else:
        outcome = "RECORDED_CHOICE_MATCH"

    return ComparisonResult(
        outcome=outcome,
        findings=findings,
        matched_consent_record_ids=matched_ids,
        requires_human_review=True,  # a match is never a publication approval
    )
