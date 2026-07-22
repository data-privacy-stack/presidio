import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class AuBankDetailsRecognizer(PatternRecognizer):
    """
    Recognises Australian bank details (BSB and account number).

    This recognizer detects Australian bank details where both:
    - a BSB (Bank State Branch) number, and
    - an account number
    are present together in the same token sequence.

    Typical formats include:
    - BSB 062-000 Account 12345678
    - 062-000 12345678

    Reference:
    - https://en.wikipedia.org/wiki/Bank_state_branch

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of recognizer
    """

    COUNTRY_CODE = "au"

    PATTERNS = [
        Pattern(
            "AU bank details (High)",
            r"\b(?:bsb)[^\S\r\n]*[:\-]?[^\S\r\n]*\d{3}[- ]?\d{3}[^\S\r\n]*(?:[,;][^\S\r\n]*)?(?:account(?:[^\S\r\n]*number)?|acct|a/c|acc(?:ount)?)[^\S\r\n]*[:\-]?[^\S\r\n]*\d{6,10}\b",  # noqa: E501
            0.5,
        ),
        Pattern(
            "AU bank details (Medium)",
            r"\b\d{3}[- ]?\d{3}[^\S\r\n]+\d{6,10}\b",
            0.2,
        ),
    ]

    CONTEXT = [
        "bsb",
        "bank",
        "account",
        "account number",
        "bank account",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "AU_BANK_DETAILS",
        name: Optional[str] = None,
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

    def validate_result(self, pattern_text: str) -> bool:
        """
        Validate structural constraints for AU bank details.

        :param pattern_text: Matched text from the regex engine.
        :return: True when text contains a plausible BSB + account pair.
        """
        digits = re.sub(r"\D", "", pattern_text)
        if len(digits) < 12 or len(digits) > 16:
            return False

        bsb = digits[:6]
        account = digits[6:]
        if len(account) < 6 or len(account) > 10:
            return False

        # Basic plausibility guard to reduce obvious false positives.
        return bsb != "000000" and account != "0" * len(account)