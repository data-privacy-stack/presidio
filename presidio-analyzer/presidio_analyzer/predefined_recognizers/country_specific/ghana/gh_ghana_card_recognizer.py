from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class GhGhanaCardRecognizer(PatternRecognizer):
    """
    Recognize Ghana Card Personal Identification Numbers (PINs).

    The Ghana Card is issued by the National Identification Authority
    of Ghana (NIA) to citizens and residents. Its Personal
    Identification Number is printed in the form GHA-XXXXXXXXX-X: the
    country code GHA, a 9-digit system number (some early cards show
    an 8-digit system number), and a trailing check digit, all
    separated by hyphens. The same number doubles as the holder's tax
    identification number (TIN) for individuals.

    Checksum note: published sources agree the trailing digit is a
    check digit, but no authoritative source publishes the check digit
    algorithm, so this recognizer implements no checksum and
    deliberately does not promote matches on an unverified one.
    Invalidation is based on structural sanity checks: the value must
    match the GHA hyphenated form, and trivial numbers such as
    all-same-digit or fully sequential runs are rejected. This follows
    the approach of the Pakistani CNIC, Saudi national ID, UAE
    Emirates ID, Egyptian national ID, Bangladesh NID and Sri Lanka NIC
    recognizers.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "gh"

    PATTERNS = [
        Pattern(
            "GH_GHANA_CARD",
            r"(?<![A-Za-z0-9])[Gg][Hh][Aa]-\d{8,9}-\d(?![A-Za-z0-9])",
            0.5,
        ),
    ]

    CONTEXT = [
        "ghana",
        "ghana card",
        "ghanaian",
        "nia",
        "national identification authority",
        "personal identification number",
        "ecowas identity card",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "GH_GHANA_CARD",
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
        Check if the pattern text cannot be a GH_GHANA_CARD entity.

        No verified checksum exists for this recognizer (see the class
        docstring), so invalidation is based on sanity checks: the
        value must be GHA, a hyphen, 8 or 9 digits, a hyphen, and one
        digit, and trivial numbers such as all-same-digit or fully
        sequential digit runs are rejected.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        parts = pattern_text.split("-")
        if len(parts) != 3:
            return True
        if parts[0].upper() != "GHA":
            return True
        if len(parts[1]) not in (8, 9) or not parts[1].isdigit():
            return True
        if len(parts[2]) != 1 or not parts[2].isdigit():
            return True
        digits = parts[1] + parts[2]
        if len(set(digits)) == 1:
            # cannot be all the same digit
            return True
        if self._is_sequential(digits):
            # a real issued PIN is never one fully sequential run
            return True
        return False

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """
        Check if the digits form a sequential run, allowing 9 to wrap to 0.

        For example, 234567890 ascends by one each step, and 321098765
        descends by one each step.

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
