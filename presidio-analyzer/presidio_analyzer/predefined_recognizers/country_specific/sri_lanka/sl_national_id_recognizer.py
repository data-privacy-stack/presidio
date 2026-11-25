from datetime import datetime
from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class SlNationalIdRecognizer(PatternRecognizer):
    """
    Recognize Sri Lanka national identity card (NIC) numbers.

    The Sri Lanka NIC is issued by the Department for Registration of
    Persons. It exists in two written forms, both still in circulation:

    - New form (since 1 January 2016): 12 digits. Digits 1-4 are the
      birth year, digits 5-7 the day of the year of birth (001-366 for
      men, 501-866 for women, i.e. 500 added to the day number), digits
      8-11 a serial number, and digit 12 a check digit.
    - Old form (before 2016): 9 digits followed by the letter V or X.
      Digits 1-2 are the birth year, digits 3-5 the day of the year
      (same 500 offset for women), digits 6-8 a serial number, digit 9
      a check digit, and the letter V (eligible to vote) or X.

    Checksum note: published sources confirm a check digit exists, but
    no authoritative source publishes the check digit algorithm, so this
    recognizer implements no checksum and deliberately does not promote
    matches on an unverified one. Invalidation is based on structural
    sanity checks: the birth year part must be within 1900 and the
    current year, the day of the year part must be a real calendar day
    for the birth year (leap years accounted for, 500 offset decoded for
    women), and trivial numbers such as all-same-digit or fully
    sequential runs are rejected. This follows the approach of the
    Pakistani CNIC, Saudi national ID, UAE Emirates ID, Egyptian
    national ID and Bangladesh NID recognizers.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "lk"

    PATTERNS = [
        Pattern(
            "LK_NATIONAL_ID (old)",
            r"(?<!\d)\d{9}[VvXx](?![A-Za-z0-9])",
            0.55,
        ),
        Pattern(
            "LK_NATIONAL_ID (12-digit)",
            r"(?<!\d)(?:19|20)\d{10}(?!\d)",
            0.5,
        ),
    ]

    CONTEXT = [
        "nic",
        "national identity card",
        "sri lanka",
        "sri lankan",
        "identity card",
        "drp",
        "registration of persons",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "LK_NATIONAL_ID",
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
        Check if the pattern text cannot be a LK_NATIONAL_ID entity.

        No verified checksum exists for this recognizer (see the class
        docstring), so invalidation is based on sanity checks: the value
        must be the 12-digit form or the 9-digit-plus-letter form, the
        birth year part must be between 1900 and the current year, the
        day of the year part must be a real calendar day for the birth
        year (decoding the 500 offset used for women), and trivial
        numbers such as all-same-digit or fully sequential runs are
        rejected.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        digits = pattern_text
        if len(pattern_text) == 10:
            if pattern_text[9] not in "VvXx" or not pattern_text[:9].isdigit():
                return True
            digits = pattern_text[:9]
            birth_year = self._full_year_from_two_digits(int(digits[0:2]))
            day_code = int(digits[2:5])
        elif len(pattern_text) == 12 and pattern_text.isdigit():
            birth_year = int(pattern_text[0:4])
            day_code = int(pattern_text[4:7])
        else:
            return True
        if len(set(digits)) == 1:
            # cannot be all the same digit
            return True
        if self._is_sequential(digits):
            # a real issued ID is never one fully sequential run
            return True
        if birth_year < 1900 or birth_year > datetime.now().year:
            return True
        if not self._valid_day_of_year(birth_year, day_code):
            return True
        return False

    @staticmethod
    def _full_year_from_two_digits(year_two_digits: int) -> int:
        """Resolve the old form's 2-digit birth year to a full year."""
        current_two_digits = datetime.now().year % 100
        if year_two_digits <= current_two_digits:
            return 2000 + year_two_digits
        return 1900 + year_two_digits

    @staticmethod
    def _valid_day_of_year(full_year: int, day_code: int) -> bool:
        """
        Check the day of the year part against the real calendar.

        The NIC adds 500 to the day number for women; day 366 exists
        only in leap years.

        :param full_year: Full birth year the day is checked against
        :param day_code: Raw 3-digit day part from the NIC
        :return: True if the day code is a real calendar day
        """
        day = day_code - 500 if day_code > 500 else day_code
        if day < 1:
            return False
        leap = full_year % 4 == 0 and (
            full_year % 100 != 0 or full_year % 400 == 0
        )
        return day <= (366 if leap else 365)

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
