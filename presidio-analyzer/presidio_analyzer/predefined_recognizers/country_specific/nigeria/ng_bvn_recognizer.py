from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class NgBvnRecognizer(PatternRecognizer):
    """
    Recognizes Nigerian Bank Verification Number (BVN).

    The BVN is an 11-digit identifier issued by the Central Bank of Nigeria
    (CBN) and managed by the Nigerian Interbank Settlement System (NIBSS).
    It links every bank account held by an individual to a single biometric
    identity record. Unauthorized access to, use of, or disclosure of a BVN
    is an offence under the CBN BVN Regulatory Framework (CBN Circular
    Ref: FPR/DIR/GEN/CIR/01/009, 2014).

    Unlike the Nigerian NIN, the BVN does not have a publicly documented
    checksum algorithm. Confidence is therefore driven primarily by context
    words rather than structural validation. Without context the base pattern
    score (0.01) is low enough to be filtered by callers applying a reasonable
    minimum score threshold (e.g. 0.35).

    Reference: https://www.cbn.gov.ng/bvn/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ng"

    PATTERNS = [
        Pattern(
            "BVN (Very Weak)",
            r"\b\d{11}\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "bvn",
        "bank verification number",
        "bank verification no",
        "bank verification",
        "nibss",
        "nigeria bank id",
        "bank identity number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "NG_BVN",
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
        Validate basic BVN format.

        Returns False (and removes the result) if the match is not exactly 11
        numeric digits. Returns None — rather than True — to preserve the
        context-boosted score instead of unconditionally promoting it to
        MAX_SCORE, since there is no checksum to provide that level of
        certainty.
        """
        if len(pattern_text) != 11 or not pattern_text.isnumeric():
            return False
        # Valid format; let context enrichment determine final confidence.
        return None
