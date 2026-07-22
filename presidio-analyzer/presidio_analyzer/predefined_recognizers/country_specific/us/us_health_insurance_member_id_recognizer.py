"""Recognizer for US health insurance member identifiers."""

from typing import Dict, List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UsHealthInsuranceMemberIdRecognizer(PatternRecognizer):
    """Recognize US health insurance member/subscriber IDs with context.

    US health insurance member identifiers are payer-specific and do not have a
    single universal checksum or format. To avoid broad matching of generic
    alphanumeric IDs, this recognizer requires both:
    - a plausible alphanumeric member ID pattern, and
    - nearby healthcare/insurance context.

    CMS consumer guidance illustrates that insurance cards carry payer-defined
    member numbers. The default regex is therefore a conservative heuristic and
    can be replaced through the ``patterns`` constructor argument.

    Reference: https://www.cms.gov/files/document/2020-c2c-how-use-health-coverage-slide-deck.pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words which increase detection confidence
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param score_thresholds: Optional default and entity-specific score thresholds
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "Health insurance member ID (alphanumeric)",
            r"\b(?=[A-Z0-9-]{6,20}\b)(?=[A-Z0-9-]*[A-Z])"
            r"(?=[A-Z0-9-]*\d)[A-Z]{1,5}-?[A-Z0-9]{5,14}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "member",
        "subscriber",
        "insurance",
        "policy",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_HEALTH_INSURANCE_MEMBER_ID",
        name: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )
        self.score_thresholds = (
            score_thresholds
            if score_thresholds is not None
            else {supported_entity: 0.6}
        )
