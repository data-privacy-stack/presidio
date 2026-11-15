from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class EgNationalIdRecognizer(PatternRecognizer):
    """
    Recognize Egypt national ID numbers.

    The Egyptian national ID is a 14-digit number issued by the Civil
    Status Organization. It is written as 14 continuous digits with no
    dashed canonical form. The digits encode:

    - digit 1: century code, 2 for births in the 1900s, 3 for the 2000s
    - digits 2-3: two-digit birth year
    - digits 4-5: birth month
    - digits 6-7: birth day
    - digits 8-9: governorate of birth code
    - digits 10-13: serial number
    - digit 14: check digit

    Checksum note: the algorithm behind the check digit is not published
    in an authoritative source, so this recognizer implements no checksum
    and deliberately does not promote matches on an unverified one. The
    only public Luhn claim found (a SlideShare deck) contradicts itself:
    its own worked example computes a checksum of 2 for an ID whose last
    digit is 3 and declares the ID invalid, which proves nothing about
    real issued IDs. An independent PyPI national-ID validator package
    describes the official check mechanism as "undisclosed". Following the
    approach of the Pakistani CNIC and UAE Emirates ID recognizers, this
    recognizer therefore identifies the number using regex, context words
    and sanity checks on the digits.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "eg"

    PATTERNS = [
        Pattern(
            "EG_NATIONAL_ID (weak)",
            r"\b\d{14}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "national id",
        "national identity",
        "egyptian id",
        "egypt",
        "national number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "EG_NATIONAL_ID",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be an EG_NATIONAL_ID entity.

        No verified checksum exists for this recognizer (see the class
        docstring), so invalidation is based on sanity checks: the value
        must be 14 digits, the century digit must be 2 or 3, the month part
        must be 01-12, the day part must be 01-31, and trivial numbers such
        as all-same-digit or fully sequential runs are rejected.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        if len(pattern_text) != 14 or not pattern_text.isnumeric():
            return True
        if pattern_text[0] not in ("2", "3"):
            return True
        if len(set(pattern_text)) == 1:
            # cannot be all the same digit
            return True
        month = int(pattern_text[3:5])
        if month < 1 or month > 12:
            return True
        day = int(pattern_text[5:7])
        if day < 1 or day > 31:
            return True
        if self._is_sequential(pattern_text):
            # a real issued ID is never one fully sequential run
            return True
        return False

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """
        Check if the digits form a sequential run, allowing 9 to wrap to 0.

        For example, 23456789012345 ascends by one each step, and
        32109876543210 descends by one each step.

        :param digits: Numeric string to check
        :return: True if every digit follows the previous one sequentially
        """
        values = [int(digit) for digit in digits]
        ascending = all(
            (values[i] + 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        descending = all(
            (values[i] - 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        return ascending or descending
