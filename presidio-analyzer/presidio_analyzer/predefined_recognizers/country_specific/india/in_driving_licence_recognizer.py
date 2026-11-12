import datetime
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class InDrivingLicenceRecognizer(PatternRecognizer):
    """
    Recognize Indian driving licence numbers.

    Since licences moved to the national Sarathi system (Ministry of Road
    Transport and Highways), a driving licence number is written in the
    standard form SS-RRYYYYNNNNNNN or SSRR YYYYNNNNNNN, i.e. 15 characters
    plus an optional separator:

      - SS: 2-letter state / union territory code (e.g. MH, HR, KA)
      - RR: 2-digit RTO (Regional Transport Office) code
      - YYYY: 4-digit year of issue
      - NNNNNNN: 7-digit serial number

    Examples (fictitious): MH14 20110062821, HR-0619850034761

    Reference: input format of the Sarathi "DL Status" service,
    https://sarathi.parivahan.gov.in/
    State/UT codes: https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_India

    Scope note: older licences printed in state-specific formats (e.g.
    "RJ-13/DLC/12/123456") must be converted to the standard form before they
    can be looked up in Sarathi and are out of scope for this recognizer.

    No checksum is published for this number, so validation only rejects
    matches with an unknown state code or an implausible year of issue; it
    never raises the score.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "in"

    PATTERNS = [
        Pattern(
            "IN Driving Licence (weak)",
            r"\b[A-Z]{2}[- ]?\d{2}[- ]?\d{4}\d{7}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "driving licence",
        "driving license",
        "driver's licence",
        "driver's license",
        "licence number",
        "license number",
        "licence no",
        "dl no",
        "dl number",
    ]

    # Current and legacy state / union territory codes
    # fmt: off
    STATE_CODES = {
        # States
        "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP", "JH", "KA", "KL",
        "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PB", "RJ", "SK", "TN", "TS",
        "TG", "TR", "UP", "UK", "WB",
        # Union territories
        "AN", "CH", "DD", "DL", "JK", "LA", "LD", "PY",
        # Legacy codes still found on older licences
        "CT", "DN", "OR", "UA", "UL", "UT",
    }
    # fmt: on

    MIN_YEAR = 1950

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IN_DRIVING_LICENCE",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            supported_entity=supported_entity,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Reject matches with an unknown state code or implausible year.

        There is no public checksum, so a plausible match is never promoted
        (returns None and the pattern score stands).

        :param pattern_text: the text to validate.
        :return: False if clearly invalid, None otherwise.
        """
        text = pattern_text.upper().replace("-", "").replace(" ", "")

        if text[:2] not in self.STATE_CODES:
            return False

        year = int(text[4:8])
        if not self.MIN_YEAR <= year <= datetime.date.today().year:
            return False

        return None
