from datetime import date
from typing import FrozenSet, List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class MySsmRecognizer(PatternRecognizer):
    """
    Recognize Malaysian SSM business and company registration numbers.

    The Companies Commission of Malaysia (SSM) has issued 12-digit
    registration numbers since 11 October 2019, written ``YYYYTTNNNNNN``:

    - ``YYYY`` is the year the entity was registered.
    - ``TT`` is the entity type: 01 local company, 02 foreign company,
      03 business, 04 local limited liability partnership (LLP),
      05 foreign LLP, 06 professional practice LLP.
    - ``NNNNNN`` is a serial number.

    There is no check digit, so validation is structural: the year must be
    between 1900 and the current year, the entity type must be 01-06, and
    the LLP types (04-06) need a year of 2012 or later, because LLPs only
    exist under the Limited Liability Partnerships Act 2012 (Act 743), in
    force since 26 December 2012. A number that passes keeps its pattern
    score and relies on context words to rise.

    Companies registered before 2019 also carry an older number, often still
    printed in brackets after the company name: up to seven digits, a dash
    and one capital letter, e.g. ``Example Sdn Bhd (123456-X)``. The letter
    is not documented, so this form is not validated and keeps a very low
    score unless context words are present: a bracketed code on its own is
    just as often a product or model code.

    Reference: https://www.ssm.com.my/Lists/Announcement/AnnouncementDetails.aspx?ID=134
               https://www.ssm.com.my/acts/Limited%20Liability%20Partnerships%20Act%202012.pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "my"

    MIN_YEAR = 1900
    # Entity type codes of the 12-digit format (SSM, 11 October 2019).
    ENTITY_TYPE_CODES: FrozenSet[str] = frozenset(["01", "02", "03", "04", "05", "06"])
    # LLP types, which only exist from the year Act 743 came into force.
    LLP_TYPE_CODES: FrozenSet[str] = frozenset(["04", "05", "06"])
    LLP_MIN_YEAR = 2012

    PATTERNS = [
        Pattern(
            "MY_SSM 12-digit (weak)",
            r"(?<!\d)(?:19|20)\d{10}(?!\d)",
            0.4,
        ),
        Pattern(
            "MY_SSM old company number (very weak)",
            # The letter stays upper case even though matching is
            # case-insensitive by default.
            r"(?<![\w-])\d{1,7}-(?-i:[A-Z])(?![\w-])",
            0.1,
        ),
    ]

    # Single words only: the default context enhancer matches each word as a
    # substring of a token, so phrases never match and short abbreviations
    # such as "reg", "co", "no", "roc" and "rob" would also match "region",
    # "cost", "phone", "process" and "problem".
    CONTEXT = [
        "ssm",
        "registration",
        "pendaftaran",
        "company",
        "syarikat",
        "sdn",
        "bhd",
        "berhad",
        "enterprise",
        "plt",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "MY_SSM",
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

    def invalidate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Reject 12-digit numbers with an impossible year or entity type.

        A structurally valid number keeps its pattern score instead of being
        raised to the maximum: without a check digit, passing these checks
        does not make a 12-digit number an SSM number. The old format has no
        documented structure, so it is never invalidated here.

        :param pattern_text: the text detected by the regex engine
        :return: True if the number cannot be an SSM number, None for the
                 old format
        """
        if "-" in pattern_text:
            return None
        if len(pattern_text) != 12 or not pattern_text.isdigit():
            return True
        year, entity_type = int(pattern_text[:4]), pattern_text[4:6]
        if not self.MIN_YEAR <= year <= date.today().year:
            return True
        if entity_type not in self.ENTITY_TYPE_CODES:
            return True
        return entity_type in self.LLP_TYPE_CODES and year < self.LLP_MIN_YEAR
