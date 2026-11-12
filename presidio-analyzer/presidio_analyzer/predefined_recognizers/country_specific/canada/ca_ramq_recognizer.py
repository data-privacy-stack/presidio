"""Recognizer for Quebec health insurance numbers (RAMQ / NAM)."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CaRamqRecognizer(PatternRecognizer):
    """Recognize Quebec health insurance numbers (RAMQ, "NAM") using regex.

    Format: 4 letters followed by 8 digits, optionally separated by a space or
    a dash between any two groups (``ABCD 1234 5678``, ``ABCD-12-34-56-78``).
    The letters are the first three of the holder's surname and the first of
    the first name; the digits are the birth year (YY), birth month (MM, with
    50 added for women), birth day (DD) and two administrative digits.

    No check digit is published for this number, so none is checked: there is no
    ``validate_result`` and a match is never promoted to full confidence.

    Two patterns share the same shape and differ only in the embedded birth
    date, so a match gets exactly one score:

    - *strong* (0.65): the month is ``01``-``12`` (men) or ``51``-``62``
      (women) and the day is ``01``-``31``;
    - *medium* (0.5): any other 4 letters + 8 digits.

    The date is used to rank matches, never to drop them: if the date structure
    below turns out to be slightly off, such numbers still match at 0.5 and the
    score threshold decides.

    Matching is case-insensitive, like the other Canadian recognizers, since
    the number may be typed in lowercase in free text.

    The structure above comes from secondary sources and has NOT been checked
    against an official RAMQ specification; the maintainers should verify it
    against RAMQ documentation.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ca"

    _SEP = r"[ -]?"
    _MONTH = r"(?:0[1-9]|1[0-2]|5[1-9]|6[0-2])"
    _DAY = r"(?:0[1-9]|[12]\d|3[01])"
    _STRONG = rf"[A-Z]{{4}}{_SEP}\d{{2}}{_SEP}{_MONTH}{_SEP}{_DAY}{_SEP}\d{{2}}\b"
    _DIGITS = rf"\d{{2}}{_SEP}\d{{2}}{_SEP}\d{{2}}{_SEP}\d{{2}}"
    _MEDIUM = rf"(?!{_STRONG})[A-Z]{{4}}{_SEP}{_DIGITS}\b"

    PATTERNS = [
        Pattern("CA RAMQ (strong)", rf"\b{_STRONG}", 0.65),
        Pattern("CA RAMQ (medium)", rf"\b{_MEDIUM}", 0.5),
    ]

    CONTEXT = [
        "ramq",
        "assurance maladie",
        "health insurance",
        "carte soleil",
        "health card",
        "medicare card",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CA_RAMQ",
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
