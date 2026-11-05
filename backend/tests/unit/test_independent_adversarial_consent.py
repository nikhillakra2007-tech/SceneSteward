"""Independent adversarial tests for the consent comparison engine.

Strictly verifies non-transitive consent, silence-is-never-agreement,
and tamper-resistance against false permission inference.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.core.choices import CONSENT_CATEGORIES
from app.services.consent_comparison import (
    compare_with_confirmed_record,
    normalize_proposed_use,
)


def _make_mock_record(choices_dict: dict[str, str]):
    class MockChoice:
        def __init__(self, category: str, choice: str):
            self.id = uuid.uuid4()
            self.category = category
            self.choice = choice
            self.evidence_reference = f"evidence:{category}"

    class MockConsentRecord:
        def __init__(self, choices: list[MockChoice]):
            self.id = uuid.uuid4()
            self.version_number = 1
            self.choices = choices

    return MockConsentRecord([MockChoice(cat, ch) for cat, ch in choices_dict.items()])


def test_adversarial_cross_category_inference():
    # Attacker scenario: Producer claims participant agreed to interview, so AI voice cloning is permitted.
    record = _make_mock_record({"interview_recording": "agreed"})
    use = SimpleNamespace(
        use_type="voice_cloning",
        platform="youtube",
        audience="global",
        purpose="synthetic narration",
        territory="worldwide",
        context_description="ai reconstructed voice",
    )
    normalized = normalize_proposed_use(use)
    result = compare_with_confirmed_record(record, [], normalized)

    # Invariant: Must NOT be agreed; outcome must be NEEDS_DISCUSSION (voice_cloning not addressed)
    assert result.outcome != "RECORDED_CHOICE_MATCH"
    assert result.outcome == "NEEDS_DISCUSSION"
    vc_finding = next((f for f in result.findings if f.get("category") == "voice_cloning"), None)
    assert vc_finding is not None
    assert vc_finding.get("choice") != "agreed"


def test_adversarial_silence_is_never_agreement():
    # Attacker scenario: Release form mentions nothing about festival submissions. Producer attempts to submit.
    record = _make_mock_record({})  # Completely silent record
    use = SimpleNamespace(
        use_type="festival_submissions",
        platform="film_festival",
        audience="festival_attendees",
        purpose="competition",
        territory="international",
        context_description="sundance screening",
    )
    normalized = normalize_proposed_use(use)
    result = compare_with_confirmed_record(record, [], normalized)

    # Invariant: Silence is never agreement
    assert result.outcome != "RECORDED_CHOICE_MATCH"
    assert result.outcome == "NEEDS_DISCUSSION"
    assert any(f.get("category") == "festival_submissions" for f in result.findings)


def test_adversarial_revocation_overrides_past_consent():
    # Attacker scenario: Participant originally agreed in v1, but in v2 expressly declined.
    v2_record = _make_mock_record({
        "interview_recording": "agreed",
        "promotional_clips": "declined",  # Explicit revocation in latest
    })
    v2_record.version_number = 2

    v1_record = _make_mock_record({
        "interview_recording": "agreed",
        "promotional_clips": "agreed",
    })
    v1_record.version_number = 1

    use = SimpleNamespace(
        use_type="promotional_clips",
        platform="social_media",
        audience="general_public",
        purpose="trailer",
        territory="worldwide",
        context_description="teaser clip",
    )
    normalized = normalize_proposed_use(use)
    result = compare_with_confirmed_record(v2_record, [v1_record], normalized)

    # Invariant: Explicit revocation in latest record marks outcome as PARTICIPANT_DECLINED
    assert result.outcome == "PARTICIPANT_DECLINED"
    promo_finding = next((f for f in result.findings if f.get("category") == "promotional_clips"), None)
    assert promo_finding is not None
    assert promo_finding.get("choice") == "declined"


def test_adversarial_composite_use_requires_all_categories_agreed():
    # Attacker scenario: Proposed use requires documentary appearance (agreed), face id (agreed),
    # but also synthetic likeness (declined).
    record = _make_mock_record({
        "documentary_appearance": "agreed",
        "face_identification": "agreed",
        "synthetic_likeness": "declined",
    })
    use = SimpleNamespace(
        use_type="synthetic_likeness",
        platform="netflix",
        audience="streaming",
        purpose="feature film",
        territory="worldwide",
        context_description="deepfake visual reconstruction",
    )
    normalized = normalize_proposed_use(use)
    result = compare_with_confirmed_record(record, [], normalized)

    # Invariant: If even ONE required category is declined, outcome is PARTICIPANT_DECLINED
    assert result.outcome != "RECORDED_CHOICE_MATCH"
    assert result.outcome == "PARTICIPANT_DECLINED"


def test_adversarial_all_15_categories_isolated():
    # Verify that agreeing to any single category never satisfies another category
    for target_cat in CONSENT_CATEGORIES:
        # Record only has target_cat agreed
        record = _make_mock_record({target_cat: "agreed"})
        for other_cat in CONSENT_CATEGORIES:
            if other_cat == target_cat:
                continue
            use = SimpleNamespace(
                use_type=other_cat,
                platform=None,
                audience=None,
                purpose=None,
                territory=None,
                context_description=None,
            )
            normalized = normalize_proposed_use(use)
            if not normalized.relevant_categories:
                continue
            result = compare_with_confirmed_record(record, [], normalized)
            other_finding = next((f for f in result.findings if f.get("category") == other_cat), None)
            if other_finding:
                assert other_finding.get("choice") != "agreed", f"Inference leak: {target_cat} leaked into {other_cat}"
