from datetime import date
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class MyNricRecognizer(PatternRecognizer):
    """
    Recognize Malaysian identity card numbers (MyKad / NRIC) using regex.

    The MyKad number issued by the National Registration Department of
    Malaysia (Jabatan Pendaftaran Negara, JPN) has 12 digits in the
    ``YYMMDD-PB-###G`` layout. It is printed with dashes and often stored
    without them:

    - ``YYMMDD``: date of birth. The two-digit year does not say the century,
      so any real calendar date is accepted (``000229`` is valid, because
      2000 was a leap year).
    - ``PB``: place-of-birth code. ``01``-``16`` and ``21``-``59`` are
      Malaysian states and federal territories, ``82`` is "state unknown",
      and ``60``-``68``, ``71``-``72``, ``74``-``79``, ``83``-``93``, ``98``
      and ``99`` are countries, regions and special categories for people
      born outside Malaysia. ``00``, ``17``-``20``, ``69``-``70``, ``73``,
      ``80``-``81`` and ``94``-``97`` are not assigned.
    - ``###G``: serial number; the last digit encodes gender (odd for male,
      even for female). Any digit is accepted.

    MyKad numbers carry no checksum, so there is no check-digit validation.
    A match whose date or place-of-birth code is impossible is invalidated;
    a structurally valid match keeps its pattern score, because about 3% of
    arbitrary 12-digit strings pass these structural checks.

    Sources:
    - JPN, "Kod Negeri" (state codes):
      https://www.jpn.gov.my/kod-negeri/
      (archived: https://web.archive.org/web/20201205090557/https://www.jpn.gov.my/kod-negeri/)
    - JPN, "Kod Negara" (country codes):
      https://www.jpn.gov.my/kod-negara/
      (archived: https://web.archive.org/web/20201205083704/https://www.jpn.gov.my/kod-negara/)
    - https://en.wikipedia.org/wiki/Malaysian_identity_card

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "my"

    NRIC_LENGTH = 12

    # Place-of-birth codes published by JPN (state codes and country codes).
    VALID_PLACE_OF_BIRTH_CODES = frozenset(
        [f"{code:02d}" for code in range(1, 17)]  # states 01-16
        + [f"{code:02d}" for code in range(21, 60)]  # states 21-59
        + [f"{code:02d}" for code in range(60, 69)]  # countries 60-68
        + ["71", "72"]  # born abroad before 2001
        + [f"{code:02d}" for code in range(74, 80)]  # countries 74-79
        + ["82"]  # state unknown
        + [f"{code:02d}" for code in range(83, 94)]  # regions 83-93
        + ["98", "99"]  # stateless, other
    )

    PATTERNS = [
        Pattern(
            "MyKad (with dashes) (medium)",
            r"\b\d{6}-\d{2}-\d{4}\b",
            0.4,
        ),
        Pattern(
            "MyKad (without dashes) (weak)",
            r"\b\d{12}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "mykad",
        "nric",
        "kad pengenalan",
        "pengenalan",
        "no. k/p",
        "k/p",
        "ic no.",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "MY_NRIC",
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Invalidate matches with an impossible birth date or place-of-birth code.

        :param pattern_text: the text detected by the regex engine
        :return: True if the match cannot be a MyKad number
        """
        digits = pattern_text.replace("-", "")
        if len(digits) != self.NRIC_LENGTH or not digits.isdigit():
            return True

        if not self._is_valid_birth_date(digits[:6]):
            return True

        return digits[6:8] not in self.VALID_PLACE_OF_BIRTH_CODES

    @staticmethod
    def _is_valid_birth_date(date_part: str) -> bool:
        """
        Check that ``YYMMDD`` is a real calendar date in some century.

        The year 2000 + YY is used: it is a leap year whenever 1900 + YY is,
        and also for YY = 00, so no valid two-digit date is rejected.
        """
        year = 2000 + int(date_part[:2])
        month = int(date_part[2:4])
        day = int(date_part[4:6])
        try:
            date(year, month, day)
        except ValueError:
            return False
        return True
