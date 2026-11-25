import calendar
from datetime import date
from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class KzIinRecognizer(PatternRecognizer):
    """
    Recognize Kazakhstan Individual Identification Numbers (IINs).

    The IIN is a 12-digit number issued to every person registered in
    Kazakhstan. Its structure is: the first six digits encode the
    holder's date of birth in YYMMDD form, the seventh digit encodes
    gender and century of birth (1 male born in the 1800s, 2 female
    born in the 1800s, 3 male born in the 1900s, 4 female born in the
    1900s, 5 male born in the 2000s, 6 female born in the 2000s), the
    next four digits are a serial number, and the last digit is a
    check digit.

    Checksum note: published secondary sources describe a two-cycle
    weighted check digit algorithm for the IIN, but no authoritative
    Kazakh source with a worked valid example was found, so this
    recognizer implements no checksum and deliberately does not
    promote matches on an unverified one. Invalidation is based on
    structural sanity checks instead: the first six digits must form
    a real calendar date in the century implied by the seventh digit,
    the seventh digit must be 1 to 6, the serial number must not be
    0000, the date must not be in the future, and trivial numbers
    such as all-same-digit or fully sequential runs are rejected.
    This follows the approach of the Pakistani CNIC, Saudi national
    ID, UAE Emirates ID, Egyptian national ID, Bangladesh NID, Sri
    Lanka NIC and Ghana Card recognizers.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "kz"

    PATTERNS = [
        Pattern(
            "KZ_IIN",
            r"(?<![A-Za-z0-9])\d{12}(?![A-Za-z0-9])",
            0.5,
        ),
    ]

    CONTEXT = [
        "kazakhstan",
        "kazakh",
        "iin",
        "individual identification number",
        "zhsn",
        "national identification",
        "kazakhstani",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "KZ_IIN",
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
        Check if the pattern text cannot be a KZ_IIN entity.

        No verified checksum exists for this recognizer (see the class
        docstring), so invalidation is based on sanity checks: the
        value must be 12 digits, the first six digits must form a real
        calendar date in the century implied by the seventh digit, the
        seventh digit must be 1 to 6, the serial number must not be
        0000, the date must not be in the future, and trivial numbers
        such as all-same-digit or fully sequential digit runs are
        rejected.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        if len(pattern_text) != 12 or not pattern_text.isdigit():
            return True
        digits = pattern_text
        if len(set(digits)) == 1:
            # cannot be all the same digit
            return True
        if self._is_sequential(digits):
            # a real issued IIN is never one fully sequential run
            return True
        century_digit = int(digits[6])
        if century_digit not in (1, 2, 3, 4, 5, 6):
            return True
        if digits[7:11] == "0000":
            return True
        if not self._valid_birth_date(digits):
            return True
        return False

    @staticmethod
    def _valid_birth_date(digits: str) -> bool:
        """
        Check the YYMMDD date against the century of the 7th digit.

        Century mapping: 1 and 2 mean the 1800s, 3 and 4 the 1900s,
        5 and 6 the 2000s. The date must be a real calendar day
        (leap-aware) and must not be in the future.

        :param digits: 12-digit IIN candidate
        :return: True if the encoded date is real and not in the future
        """
        century_map = {1: 1800, 2: 1800, 3: 1900, 4: 1900, 5: 2000, 6: 2000}
        century = century_map.get(int(digits[6]))
        if century is None:
            return False
        year = century + int(digits[0:2])
        month = int(digits[2:4])
        day = int(digits[4:6])
        if month < 1 or month > 12:
            return False
        if day < 1 or day > calendar.monthrange(year, month)[1]:
            return False
        if date(year, month, day) > date.today():
            return False
        return True

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """
        Check if the digits form a sequential run, allowing 9 to wrap to 0.

        For example, 234567890123 ascends by one each step, and
        321098765432 descends by one each step.

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
