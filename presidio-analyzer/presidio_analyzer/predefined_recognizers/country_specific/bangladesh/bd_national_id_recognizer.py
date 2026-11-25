from datetime import datetime
from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class BdNationalIdRecognizer(PatternRecognizer):
    """
    Recognize Bangladesh national ID (NID) numbers.

    The Bangladesh National ID is issued by the Election Commission. It
    exists in three written forms:

    - 17 digits: the full form used in official SMS services and the
      smart card system. Digits 1-4 are the birth year, digits 5-6 the
      district code, digit 7 the RMO code, digits 8-9 the upazila code,
      digits 10-11 the union code, and digits 12-17 a unique serial
      number. A 13-digit NID is converted to this form by prepending the
      birth year.
    - 13 digits: the older laminated card form, which is the 17-digit
      form without the birth year prefix.
    - 10 digits: the newer smart NID card number.

    Checksum note: no authoritative source describes a check digit or
    checksum algorithm for the Bangladesh NID, so this recognizer
    implements no checksum and deliberately does not promote matches on
    an unverified one. Invalidation is based on structural sanity
    checks: the birth year part must be within 1900 and the current
    year, the district code part must be 01 to 64 (Bangladesh has 64
    districts), and trivial numbers such as all-same-digit or fully
    sequential runs are rejected. This follows the approach of the
    Pakistani CNIC, Saudi national ID, UAE Emirates ID and Egyptian
    national ID recognizers.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "bd"

    PATTERNS = [
        Pattern(
            "BD_NATIONAL_ID (17-digit)",
            r"(?<!\d)(?:19|20)\d{15}(?!\d)",
            0.55,
        ),
        Pattern(
            "BD_NATIONAL_ID (13-digit)",
            r"(?<!\d)\d{13}(?!\d)",
            0.4,
        ),
        Pattern(
            "BD_NATIONAL_ID (weak)",
            r"(?<!\d)\d{10}(?!\d)",
            0.3,
        ),
    ]

    CONTEXT = [
        "nid",
        "national id",
        "national identity",
        "bangladesh",
        "smart card",
        "voter id",
        "birth registration",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "BD_NATIONAL_ID",
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
        Check if the pattern text cannot be a BD_NATIONAL_ID entity.

        No verified checksum exists for this recognizer (see the class
        docstring), so invalidation is based on sanity checks: the value
        must be 10, 13 or 17 digits, the 17-digit birth year part must be
        between 1900 and the current year, the district code part (first
        two digits of the 13-digit core) must be 01 to 64, and trivial
        numbers such as all-same-digit or fully sequential runs are
        rejected.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        if len(pattern_text) not in (10, 13, 17) or not pattern_text.isnumeric():
            return True
        if len(set(pattern_text)) == 1:
            # cannot be all the same digit
            return True
        if self._is_sequential(pattern_text):
            # a real issued ID is never one fully sequential run
            return True
        if len(pattern_text) == 17:
            birth_year = int(pattern_text[0:4])
            if birth_year < 1900 or birth_year > datetime.now().year:
                return True
            district_code = int(pattern_text[4:6])
        elif len(pattern_text) == 13:
            district_code = int(pattern_text[0:2])
        else:
            # the 10-digit smart NID has no published internal structure
            return False
        if district_code < 1 or district_code > 64:
            return True
        return False

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """
        Check if the digits form a sequential run, allowing 9 to wrap to 0.

        For example, 23456789012345678 ascends by one each step, and
        32109876543210987 descends by one each step.

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
