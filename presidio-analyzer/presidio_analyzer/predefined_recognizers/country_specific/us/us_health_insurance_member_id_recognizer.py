"""Recognizer for US health insurance member identifiers."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult


class UsHealthInsuranceMemberIdRecognizer(PatternRecognizer):
    """Recognize US health insurance member/subscriber IDs with context.

    US health insurance member identifiers are payer-specific and do not have a
    single universal checksum or format. To avoid broad matching of generic
    alphanumeric IDs, this recognizer requires both:
    - a plausible alphanumeric member ID pattern, and
    - nearby healthcare/insurance context.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to require near a match
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param context_window: Number of characters before/after a match to scan
    for context.
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
        "member id",
        "member number",
        "subscriber id",
        "subscriber number",
        "insurance id",
        "health plan id",
        "plan member id",
        "policy id",
        "policy number",
        "health insurance",
        "insurance member",
        "insurance card",
    ]

    NEGATIVE_CONTEXT = [
        "order number",
        "order no",
        "tracking number",
        "tracking no",
        "case number",
        "case no",
        "claim number",
        "claim no",
        "claim id",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_HEALTH_INSURANCE_MEMBER_ID",
        name: Optional[str] = None,
        context_window: int = 40,
    ):
        self.context_window = context_window
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts=None,
        regex_flags: Optional[int] = None,
    ) -> List[RecognizerResult]:
        """Analyze text and keep only matches with nearby positive context."""
        results = super().analyze(text, entities, nlp_artifacts, regex_flags)
        return [
            result for result in results if self.__has_required_context(text, result)
        ]

    def __has_required_context(self, text: str, result: RecognizerResult) -> bool:
        window_text = self.__get_context_window(text, result).lower()
        if any(context in window_text for context in self.NEGATIVE_CONTEXT):
            return False
        return any(context in window_text for context in self.context)

    def __get_context_window(self, text: str, result: RecognizerResult) -> str:
        start = max(0, result.start - self.context_window)
        end = min(len(text), result.end + self.context_window)
        return text[start:end]
