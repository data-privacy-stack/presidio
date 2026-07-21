from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class KeNationalIdRecognizer(PatternRecognizer):
    """
    Recognizes Kenyan National Identity Card numbers.

    The Kenyan National Identity Card (ID card) is issued by the National
    Registration Bureau under the Registration of Persons Act (Cap. 107).
    The card number is a 7- or 8-digit sequential identifier unique to each
    cardholder. Cards issued since the late 1990s typically carry an 8-digit
    number; earlier cards may have 7 digits.

    No checksum algorithm is publicly documented for Kenyan national ID
    numbers. Confidence is therefore driven primarily by context words.
    Without context the base score (0.01) is intentionally low enough to be
    filtered by callers applying a reasonable minimum threshold (e.g. 0.35).

    Reference: https://www.ecitizen.go.ke/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ke"

    # 7- or 8-digit national ID number, not embedded in a longer number.
    PATTERNS = [
        Pattern(
            "KE National ID (Very Weak)",
            r"\b\d{7,8}\b",
            0.01,
        ),
    ]

    CONTEXT = [
        # Single-token entries — matched against individual spaCy lemmas by
        # LemmaContextAwareEnhancer (substring mode). Multi-word phrases alone
        # are never matched because the enhancer compares against single tokens.
        "kenya",
        "kenyan",
        "national",
        "nid",
        "registration",
        # Multi-word entries — only effective when the enhancer is given
        # pre-tokenised context via the `context` parameter.
        "national id",
        "national identity",
        "national identity card",
        "id number",
        "kenyan id",
        "kenya national id",
        "registration number",
        "id card",
        "national registration",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "KE_NATIONAL_ID",
        name: Optional[str] = None,
    ) -> None:
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Validate basic Kenyan national ID format.

        Returns False (and removes the result) if the match is not 7 or 8
        numeric digits. Returns None to preserve the context-boosted score
        rather than unconditionally promoting to MAX_SCORE, since no checksum
        is available to justify that level of certainty.
        """
        if not pattern_text.isnumeric() or len(pattern_text) not in (7, 8):
            return False
        return None
