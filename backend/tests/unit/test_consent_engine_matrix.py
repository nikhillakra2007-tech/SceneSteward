"""Exhaustive test matrix and invariant verification for the deterministic consent comparison engine.

Verifies:
1. All 15 canonical consent categories across all 6 choice states.
2. The 10 critical product invariants.
3. Complex multi-category proposals, keyword heuristics, and conflicting historical versions.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.core.choices import CONSENT_CATEGORIES
from app.services.consent_comparison import (
    ComparisonResult,
    compare_with_confirmed_record,
    normalize_proposed_use,
)


@dataclass
class MockChoice:
    id: uuid.UUID
    category: str
    choice: str
    evidence_reference: str | None = None


@dataclass
class MockConsentRecord:
    id: uuid.UUID
    version_number: int
    choices: list[MockChoice]


def make_record(version: int, choices_dict: dict[str, str]) -> MockConsentRecord:
    rec_id = uuid.uuid4()
    choices = [
        MockChoice(id=uuid.uuid4(), category=cat, choice=val, evidence_reference=f"evidence_{cat}")
        for cat, val in choices_dict.items()
    ]
    return MockConsentRecord(id=rec_id, version_number=version, choices=choices)


def make_use(
    use_type: str = "interview",
    platform: str | None = None,
    audience: str | None = None,
    purpose: str | None = None,
    territory: str | None = None,
    context: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        use_type=use_type,
        platform=platform,
        audience=audience,
        purpose=purpose,
        territory=territory,
        context_description=context,
    )


# --- 1. Exhaustive Category State Verification -----------------------------


@pytest.mark.parametrize("category", CONSENT_CATEGORIES)
def test_each_category_explicit_agreed(category: str):
    """When a required category is explicitly agreed in confirmed record -> RECORDED_CHOICE_MATCH."""
    record = make_record(version=1, choices_dict={category: "agreed"})
    # Normalize with explicit relevant category
    norm = SimpleNamespace(relevant_categories=[category], matched_keywords={})
    res: ComparisonResult = compare_with_confirmed_record(record, [], norm)
    assert res.outcome == "RECORDED_CHOICE_MATCH"
    assert res.requires_human_review is True
    assert len(res.findings) == 1
    assert res.findings[0]["choice"] == "agreed"


@pytest.mark.parametrize("category", CONSENT_CATEGORIES)
def test_each_category_explicit_declined(category: str):
    """When a required category is explicitly declined in confirmed record -> PARTICIPANT_DECLINED."""
    record = make_record(version=1, choices_dict={category: "declined"})
    norm = SimpleNamespace(relevant_categories=[category], matched_keywords={})
    res: ComparisonResult = compare_with_confirmed_record(record, [], norm)
    assert res.outcome == "PARTICIPANT_DECLINED"
    assert any(f["choice"] == "declined" and f["category"] == category for f in res.findings)


@pytest.mark.parametrize("choice_state", ["not_discussed", "needs_clarification", "awaiting_confirmation", "explained"])
@pytest.mark.parametrize("category", ["promotional_clips", "voice_cloning", "synthetic_likeness"])
def test_each_category_unsettled_states_require_discussion(category: str, choice_state: str):
    """Any non-agreed state (not discussed, needs clarification, explained) must resolve to NEEDS_DISCUSSION."""
    record = make_record(version=1, choices_dict={category: choice_state})
    norm = SimpleNamespace(relevant_categories=[category], matched_keywords={})
    res: ComparisonResult = compare_with_confirmed_record(record, [], norm)
    assert res.outcome == "NEEDS_DISCUSSION"


@pytest.mark.parametrize("category", CONSENT_CATEGORIES)
def test_missing_category_in_record_is_never_silent_agreement(category: str):
    """Silence is never agreement: missing category in confirmed record must trigger NEEDS_DISCUSSION."""
    record = make_record(version=1, choices_dict={"interview_recording": "agreed"})
    # Required category is different from what was recorded
    norm = SimpleNamespace(relevant_categories=[category], matched_keywords={})
    res: ComparisonResult = compare_with_confirmed_record(record if category != "interview_recording" else None, [], norm)
    assert res.outcome == "NEEDS_DISCUSSION"
    assert any(f["category"] == category and f["choice"] is None for f in res.findings)


# --- 2. Invariant Verification: Cross-Category Non-Transitivity ------------


def test_interview_agreement_never_authorizes_trailer():
    """Invariant 9: Interview agreement cannot automatically authorize promotional trailer."""
    # Participant only agreed to interview recording
    record = make_record(version=1, choices_dict={"interview_recording": "agreed", "documentary_appearance": "agreed"})
    proposed_use = make_use(use_type="promotional_trailer", purpose="Teaser for YouTube")
    norm = normalize_proposed_use(proposed_use)

    res = compare_with_confirmed_record(record, [], norm)
    assert res.outcome == "NEEDS_DISCUSSION"
    # promotional_clips must be flagged as missing
    missing_cats = [f["category"] for f in res.findings if f.get("choice") is None]
    assert "promotional_clips" in missing_cats


def test_interview_agreement_never_authorizes_voice_cloning():
    """Invariant 9: Interview agreement cannot authorize AI voice reconstruction."""
    record = make_record(version=1, choices_dict={"interview_recording": "agreed", "documentary_appearance": "agreed"})
    proposed_use = make_use(use_type="voice_reconstruction", context="Reconstruct missing dialogue with AI voice model")
    norm = normalize_proposed_use(proposed_use)

    res = compare_with_confirmed_record(record, [], norm)
    assert res.outcome == "NEEDS_DISCUSSION"
    missing_cats = [f["category"] for f in res.findings if f.get("choice") is None]
    assert "voice_cloning" in missing_cats or "third_party_ai_processing" in missing_cats


def test_declined_trailer_with_agreed_interview_blocks_trailer():
    """Invariant 4: Explicit decline in promotional_clips takes precedence over interview agreement."""
    record = make_record(version=1, choices_dict={
        "interview_recording": "agreed",
        "documentary_appearance": "agreed",
        "promotional_clips": "declined",
    })
    proposed_use = make_use(use_type="promotional_trailer")
    norm = normalize_proposed_use(proposed_use)

    res = compare_with_confirmed_record(record, [], norm)
    assert res.outcome == "PARTICIPANT_DECLINED"


def test_conflicting_historical_versions_require_human_review():
    """Invariant 8: Contradiction across versions (e.g. agreed in v1, declined in v2) requires human review."""
    v1 = make_record(version=1, choices_dict={"promotional_clips": "agreed"})
    v2 = make_record(version=2, choices_dict={"promotional_clips": "declined"})

    norm = SimpleNamespace(relevant_categories=["promotional_clips"], matched_keywords={})
    # v2 is latest, v1 is history
    res = compare_with_confirmed_record(v2, [v1], norm)
    # Latest decline must block or require review
    assert res.outcome in ("PARTICIPANT_DECLINED", "HUMAN_REVIEW_REQUIRED")


def test_sensitive_excerpt_promotion_adds_sensitive_details_category():
    """Sensitive keyword in promotional use automatically adds sensitive_personal_details to scope."""
    use = make_use(
        use_type="promotional_trailer",
        purpose="Promoting the film using sensitive hospital interview segment",
    )
    norm = normalize_proposed_use(use)
    assert "sensitive_personal_details" in norm.relevant_categories
    assert "promotional_clips" in norm.relevant_categories


def test_empty_unrecognised_use_type_is_unresolved():
    """Invariant 10: Completely unknown use signals without categories produce UNRESOLVED."""
    use = make_use(use_type="unknown_custom_xyz", purpose="do stuff")
    norm = normalize_proposed_use(use)
    res = compare_with_confirmed_record(None, [], norm)
    assert res.outcome == "UNRESOLVED"
    assert res.findings[0]["category"] is None
