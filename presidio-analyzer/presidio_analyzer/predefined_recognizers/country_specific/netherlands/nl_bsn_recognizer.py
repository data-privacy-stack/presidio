"""Dutch citizen service number (burgerservicenummer, BSN) recognizer."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class NlBsnRecognizer(PatternRecognizer):
    """Recognize the Dutch citizen service number (burgerservicenummer, BSN).

    A BSN is nine digits. Numbers issued as eight digits are written with a
    leading zero. The number is usually written unbroken (``123456782``) and
    sometimes grouped as ``1234.56.782`` or ``1234 56 782``.

    Validation follows the "elfproef" (eleven test) from the Rijksdienst voor
    Identiteitsgegevens (RvIG) specification *Logisch Ontwerp BSN*: with digits
    d1..d9, ``9*d1 + 8*d2 + 7*d3 + 6*d4 + 5*d5 + 4*d6 + 3*d7 + 2*d8 - 1*d9``
    must be divisible by 11. The final weight is -1, unlike the +1 used by the
    eleven test for old Dutch bank account numbers.

    Every issued BSN passes the eleven test, so a number that fails it is
    dropped. Roughly one in eleven arbitrary nine-digit numbers also passes,
    so passing does not raise the score: it stays at the pattern score and
    context words such as "BSN" or "burgerservicenummer" raise it.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "nl"

    PATTERNS = [
        Pattern(
            "BSN (very weak)",
            r"\b\d{9}\b",
            0.05,
        ),
        Pattern(
            "BSN grouped (weak)",
            r"\b\d{4}([. ])\d{2}\1\d{3}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "burgerservicenummer",
        "bsn",
        "sofinummer",
        "sofi-nummer",
        "citizen service number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "nl",
        supported_entity: str = "NL_BSN",
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

    @staticmethod
    def _digits(pattern_text: str) -> str:
        return "".join(c for c in pattern_text if c.isdigit())

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """Drop numbers that fail the eleven test.

        Returns ``False`` for a number that cannot be a BSN, and ``None`` for
        one that passes, so the pattern score stands.
        """
        digits = self._digits(pattern_text)
        if len(digits) != 9:
            return False

        weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
        total = sum(w * int(d) for w, d in zip(weights, digits))
        if total % 11 != 0:
            return False
        return None

    def invalidate_result(self, pattern_text: str) -> bool:
        """Reject all-zero numbers, which pass the eleven test trivially."""
        return int(self._digits(pattern_text) or "0") == 0
