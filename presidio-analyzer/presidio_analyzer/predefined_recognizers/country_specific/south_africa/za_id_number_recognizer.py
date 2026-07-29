from datetime import date
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class ZaIdNumberRecognizer(PatternRecognizer):
    """
    Recognize South African ID numbers using regex and structural validation.

    South African identity numbers are 13 digits in the ``YYMMDDSSSSCAZ``
    layout:
    - ``YYMMDD``: date of birth (two-digit year mapped to a full year using a
      rolling pivot: if ``YY`` is greater than the last two digits of the
      current calendar year, the year is interpreted as 19YY; otherwise 20YY.
      The resulting date must be valid and cannot be in the future.)
    - ``SSSS``: sequence number
    - ``C``: citizenship / status — 0 = SA citizen, 1 = permanent resident,
      2 = refugee
    - ``A``: obsolete race-classification digit (typically 8 or 9)
    - ``Z``: check digit using the Luhn algorithm

    Reference:
    https://en.wikipedia.org/wiki/South_African_identity_card#Identity_Number
    https://www.irb-cisr.gc.ca/en/country-information/rir/Pages/index.aspx?doc=454798

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "za"

    ID_LENGTH = 13
    BIRTH_DATE_LENGTH = 6
    CITIZENSHIP_INDEX = 10
    LEGACY_RACE_INDEX = 11
    ALLOWED_CITIZENSHIP_VALUES = frozenset({"0", "1", "2"})
    ALLOWED_LEGACY_RACE_VALUES = frozenset({"8", "9"})

    PATTERNS = [
        Pattern(
            "South African ID Number",
            r"\b\d{10}[0-2][89]\d\b",
            0.2,
        ),
    ]

    CONTEXT = [
        "id",
        "identity",
        "identity number",
        "id number",
        "south african id",
        "rsa id",
        "smart id",
        "national id",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_ID_NUMBER",
        name: Optional[str] = None,
    ):
        patterns = self.PATTERNS if patterns is None else patterns
        context = self.CONTEXT if context is None else context
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        if len(pattern_text) != self.ID_LENGTH or not pattern_text.isdigit():
            return False

        if not self._has_valid_birth_date(pattern_text[: self.BIRTH_DATE_LENGTH]):
            return False

        if pattern_text[self.CITIZENSHIP_INDEX] not in self.ALLOWED_CITIZENSHIP_VALUES:
            return False

        if pattern_text[self.LEGACY_RACE_INDEX] not in self.ALLOWED_LEGACY_RACE_VALUES:
            return False

        return self._is_luhn_valid(pattern_text)

    @staticmethod
    def _has_valid_birth_date(date_part: str) -> bool:
        month = int(date_part[2:4])
        day = int(date_part[4:6])
        year_suffix = int(date_part[:2])

        today = date.today()
        pivot = today.year % 100
        century = 1900 if year_suffix > pivot else 2000

        try:
            birth_date = date(century + year_suffix, month, day)
        except ValueError:
            return False

        return birth_date <= today

    @staticmethod
    def _is_luhn_valid(value: str) -> bool:
        digits = [int(digit) for digit in value]
        checksum = 0
        parity = len(digits) % 2

        for index, digit in enumerate(digits):
            if index % 2 == parity:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0
