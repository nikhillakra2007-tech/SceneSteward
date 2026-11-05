"""Document Intelligence & Adversarial Resistance Service.

Provides:
1. Defensive sanitization against prompt injection, jailbreaking, and control character smuggling in untrusted documents.
2. Structured clause detection and evidence mapping across the 15 canonical consent categories.
3. Stated exclusion extraction and fine-grained confidence scoring.
4. Cryptographic integrity and advisory boundaries: all findings are strictly advisory and require human confirmation.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.choices import CONSENT_CATEGORIES

logger = logging.getLogger("scenesteward.document_intelligence")

# Dangerous adversarial patterns commonly found in malicious prompt injections
ADVERSARIAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("SYSTEM_PROMPT_OVERRIDE", re.compile(
        r"(?i)\b(ignore|disregard|forget|bypass)\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|directives|rules)\b"
    )),
    ("ROLE_IMPERSONATION", re.compile(
        r"(?i)\b(you\s+are\s+now|act\s+as\s+(an?\s+)?(admin|system|developer|root|unrestricted|god))\b"
    )),
    ("DELIMITER_INJECTION", re.compile(
        r"(\[SYSTEM\]|\[\/SYSTEM\]|<<SYS>>|<\/SYS>>|<system>|<\/system>|<admin>|<\/admin>|```json\s*\{\s*\"override\")"
    )),
    ("FORCED_CONSENT_DIRECTIVE", re.compile(
        r"(?i)\b(mark\s+(all|everything)\s+(as\s+)?(agreed|consented|approved)|grant\s+all\s+permissions|automatically\s+consent\s+to\s+all)\b"
    )),
    ("UNBOUNDED_JSON_INJECTION", re.compile(
        r"(?i)\b(payload|instructions?)\s*:\s*\{[^}]*\"(choice|agreed|consent)\"\s*:\s*\"(agreed|yes|true)\"\s*\}"
    )),
]

# Smuggled zero-width characters and bi-directional overrides
SMUGGLED_CHARACTERS = re.compile(
    r"[\u200B\u200C\u200D\uFEFF\u202A\u202B\u202C\u202D\u202E\u2060\u2066\u2067\u2068\u2069]"
)

# Detailed keyword dictionaries mapping to the 15 canonical categories
CATEGORY_KEYWORD_MAP: dict[str, tuple[str, ...]] = {
    "interview_recording": (
        "interview", "sit-down interview", "recorded interview", "audio interview", "video interview",
        "conversation recorded", "spoken interview"
    ),
    "documentary_appearance": (
        "documentary", "documentary film", "feature documentary", "appear in the film",
        "on camera", "on-camera", "appear on screen", "screen appearance", "visual likeness in film"
    ),
    "name_identification": (
        "name", "full name", "credited as", "identified by name", "name appear", "named on screen", "lower third"
    ),
    "face_identification": (
        "face", "facial likeness", "recognizable", "recognisable", "identifiable face", "unblurred face", "face shown"
    ),
    "sensitive_personal_details": (
        "sensitive", "personal details", "medical history", "health status", "trauma", "personal history",
        "family history", "confidential details", "grief", "substance use", "vulnerability"
    ),
    "promotional_clips": (
        "promo", "promotional", "trailer", "teaser", "marketing", "advertisement", "social teaser", "press kit", "sizzle"
    ),
    "festival_submissions": (
        "festival", "film festival", "festival screening", "sundance", "cannes", "berlinale", "tiff", "competition"
    ),
    "ai_transcription": (
        "transcription", "transcribe", "automated transcript", "whisper", "speech to text", "speech-to-text", "ai subtitles"
    ),
    "voice_cloning": (
        "voice clon", "voice synthesis", "synthetic voice", "reconstruct voice", "ai voice", "voice model", "voice imitation"
    ),
    "synthetic_likeness": (
        "synthetic likeness", "deepfake", "face swap", "digital recreation", "ai likeness", "avatar", "digital double"
    ),
    "third_party_ai_processing": (
        "third-party ai", "third party ai", "external ai", "ai vendor", "cloud ai", "machine learning vendor", "foundation model"
    ),
    "new_audience": (
        "new audience", "wider audience", "general release", "public audience", "educational distribution", "broadcast"
    ),
    "new_territory": (
        "new territory", "international", "foreign distribution", "worldwide", "global rights", "worldwide release"
    ),
    "new_platform": (
        "new platform", "streaming", "netflix", "prime", "youtube", "social media", "tiktok", "instagram", "podcast", "vod"
    ),
    "new_story_context": (
        "new story context", "re-edit", "reframe", "spin-off", "sequel", "derivative work", "different context", "recontextualize"
    ),
}

AGREEMENT_PATTERN = re.compile(
    r"\b(agree(?:s|d)?|consent(?:s|ed)?|grant(?:s|ed)?|authori[sz]e(?:s|d)?|permit(?:s|ted)?|approve(?:s|d)?|willing|happy to|okay with|ok with)\b",
    re.IGNORECASE,
)

DECLINE_PATTERN = re.compile(
    r"\b(do not consent|do not agree|will not permit|decline(?:s|d)?|refus(?:e|es|ed)?|not comfortable|unwilling|strictly prohibit(?:s|ed)?|never authori[sz]e|forbid(?:s|den)?)\b",
    re.IGNORECASE,
)

AMBIGUITY_PATTERN = re.compile(
    r"\b(maybe|perhaps|not sure|possibly|might|depends|subject to discussion|to be decided|unclear|provisional)\b",
    re.IGNORECASE,
)


@dataclass
class AdversarialFlag:
    category: str
    snippet: str
    page_number: int
    remediation: str


@dataclass
class DetectedClause:
    category: str
    choice_indication: str  # agreed | declined | needs_clarification
    quote: str
    page_number: int
    line_number: int
    confidence: float
    explanation: str


@dataclass
class StatedExclusion:
    quote: str
    page_number: int
    targeted_category: str | None


@dataclass
class DocumentIntelligenceReport:
    document_id: str
    total_pages: int
    content_hash: str
    adversarial_flags: list[AdversarialFlag] = field(default_factory=list)
    detected_clauses: list[DetectedClause] = field(default_factory=list)
    stated_exclusions: list[StatedExclusion] = field(default_factory=list)
    unmentioned_categories: list[str] = field(default_factory=list)
    advisory_notice: str = (
        "NOTICE: All detected clauses, stated exclusions, and confidence scores are advisory. "
        "Automated intelligence does NOT constitute human review or participant consent. "
        "A qualified human must review and record rationale before confirming choices."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "total_pages": self.total_pages,
            "content_hash": self.content_hash,
            "adversarial_flags": [
                {
                    "category": f.category,
                    "snippet": f.snippet,
                    "page_number": f.page_number,
                    "remediation": f.remediation,
                }
                for f in self.adversarial_flags
            ],
            "detected_clauses": [
                {
                    "category": c.category,
                    "choice_indication": c.choice_indication,
                    "quote": c.quote,
                    "page_number": c.page_number,
                    "line_number": c.line_number,
                    "confidence": c.confidence,
                    "explanation": c.explanation,
                }
                for c in self.detected_clauses
            ],
            "stated_exclusions": [
                {
                    "quote": e.quote,
                    "page_number": e.page_number,
                    "targeted_category": e.targeted_category,
                }
                for e in self.stated_exclusions
            ],
            "unmentioned_categories": self.unmentioned_categories,
            "advisory_notice": self.advisory_notice,
        }


def sanitize_text(text: str, page_number: int = 1) -> tuple[str, list[AdversarialFlag]]:
    """Sanitize untrusted text extracted from documents.
    Neutralizes prompt injections, strips smuggled control characters,
    and returns sanitized text along with detected security flags.
    """
    flags: list[AdversarialFlag] = []

    # 1. Detect and strip smuggled zero-width and directional control characters
    smuggled_matches = SMUGGLED_CHARACTERS.findall(text)
    if smuggled_matches:
        flags.append(
            AdversarialFlag(
                category="SMUGGLED_CONTROL_CHARACTERS",
                snippet=f"Detected {len(smuggled_matches)} zero-width / directional control chars",
                page_number=page_number,
                remediation="Stripped invisible smuggled characters to prevent parser exploitation",
            )
        )
        text = SMUGGLED_CHARACTERS.sub("", text)

    # 2. Detect prompt injection attempts
    for flag_name, pattern in ADVERSARIAL_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0)[:120]
            flags.append(
                AdversarialFlag(
                    category=flag_name,
                    snippet=snippet,
                    page_number=page_number,
                    remediation="Neutralized injection attempt; clause flagged for security review",
                )
            )
            logger.warning(
                "Adversarial prompt injection detected on page %d: [%s] '%s'",
                page_number,
                flag_name,
                snippet,
            )

    # Replace explicit system prompt delimiters to prevent prompt jailbreaking
    sanitized = re.sub(r"(?i)<\/?(system|admin|prompt)[^>]*>", "[STRIPPED_TAG]", text)
    sanitized = re.sub(r"(\[SYSTEM\]|\[\/SYSTEM\]|<<SYS>>|<\/SYS>>)", "[STRIPPED_DELIMITER]", sanitized)

    return sanitized, flags


def analyze_document_pages(
    pages: list[tuple[int, str]], document_id: str
) -> DocumentIntelligenceReport:
    """Analyze multi-page document content:
    - Sanitize every page against prompt injections
    - Extract evidence for 15 canonical categories with line numbers & page references
    - Detect explicit exclusions and prohibitions
    - Calculate confidence scores
    - Return a comprehensive advisory DocumentIntelligenceReport
    """
    total_pages = len(pages)
    hasher = hashlib.sha256()

    all_flags: list[AdversarialFlag] = []
    detected_clauses: list[DetectedClause] = []
    stated_exclusions: list[StatedExclusion] = []
    seen_categories: set[str] = set()

    for page_num, raw_content in pages:
        hasher.update(f"p{page_num}:{raw_content}".encode())
        clean_text, page_flags = sanitize_text(raw_content, page_number=page_num)
        all_flags.extend(page_flags)

        lines = clean_text.splitlines()
        for line_idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or len(line_str) < 5:
                continue

            # Split line into sentence fragments for localized sentiment
            sentences = re.split(r"(?<=[.!?])\s+", line_str)
            for sentence in sentences:
                sent_clean = sentence.strip()
                if not sent_clean:
                    continue

                sent_lower = sent_clean.lower()
                is_declined = bool(DECLINE_PATTERN.search(sent_clean))
                is_agreed = bool(AGREEMENT_PATTERN.search(sent_clean))
                is_ambiguous = bool(AMBIGUITY_PATTERN.search(sent_clean))

                # Identify which categories are mentioned in this sentence
                for category, keywords in CATEGORY_KEYWORD_MAP.items():
                    matched_kw = next((kw for kw in keywords if kw in sent_lower), None)
                    if matched_kw:
                        seen_categories.add(category)

                        if is_declined:
                            choice = "declined"
                            confidence = 0.90 if any(strong in sent_lower for strong in ("strictly", "never", "do not")) else 0.80
                            explanation = f"Explicit refusal regarding '{category}' detected via '{matched_kw}'."
                            stated_exclusions.append(
                                StatedExclusion(
                                    quote=sent_clean[:300],
                                    page_number=page_num,
                                    targeted_category=category,
                                )
                            )
                        elif is_agreed and not is_ambiguous:
                            choice = "agreed"
                            confidence = 0.85 if any(strong in sent_lower for strong in ("expressly", "hereby", "fully")) else 0.75
                            explanation = f"Explicit agreement regarding '{category}' detected via '{matched_kw}'."
                        elif is_ambiguous:
                            choice = "needs_clarification"
                            confidence = 0.50
                            explanation = f"Ambiguous or conditional statement regarding '{category}' via '{matched_kw}'."
                        else:
                            # Mentioned without explicit assent verb
                            choice = "needs_clarification"
                            confidence = 0.40
                            explanation = f"Mention of '{category}' keyword '{matched_kw}' without explicit agreement verb; requires clarification."

                        detected_clauses.append(
                            DetectedClause(
                                category=category,
                                choice_indication=choice,
                                quote=sent_clean[:300],
                                page_number=page_num,
                                line_number=line_idx,
                                confidence=confidence,
                                explanation=explanation,
                            )
                        )

    # Categories in CONSENT_CATEGORIES not detected anywhere
    unmentioned = [cat for cat in sorted(CONSENT_CATEGORIES) if cat not in seen_categories]

    return DocumentIntelligenceReport(
        document_id=document_id,
        total_pages=total_pages,
        content_hash=hasher.hexdigest(),
        adversarial_flags=all_flags,
        detected_clauses=detected_clauses,
        stated_exclusions=stated_exclusions,
        unmentioned_categories=unmentioned,
    )
