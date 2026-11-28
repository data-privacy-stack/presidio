from datetime import datetime
from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class InDrivingLicenceRecognizer(PatternRecognizer):
    """
    Recognizes Indian Driving Licence numbers issued by RTOs.

    The Indian driving licence number is a 15-character identifier with the
    format SS-RR-YYYYNNNNNNN where SS is the 2-letter state/UT code, RR is
    the 2-digit RTO code, YYYY is the 4-digit year of issue, and NNNNNNN is
    a 7-digit serial number.

    Reference: https://en.wikipedia.org/wiki/Driving_licence_in_India

    No published checksum algorithm exists for Indian driving licences, so
    ``validate_result`` only checks the state/UT code and year of issue.
    It returns ``None`` (plausible) on a valid code and year, never ``True``.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
        for different strings to be used during pattern matching.
        This can allow a greater variety in input, for example by removing
        dashes or spaces.
    """

    COUNTRY_CODE = "in"

    PATTERNS = [
        Pattern(
            "Indian Driving Licence (Medium)",
            r"\b[A-Z]{2}[- ]?\d{2}[- ]?\d{4}\d{7}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "driving licence",
        "driving license",
        "licence number",
        "license number",
        "dl no",
        "dl number",
        "driving permit",
    ]

    # fmt: off
    VALID_STATE_CODES = {
        # States
        "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP", "JH",
        "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PB",
        "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "WB", "UT",
        # Union Territories
        "AN", "CH", "DH", "DL", "JK", "LA", "LD", "PY",
        # Old/legacy codes
        "UL", "OR", "UA", "CT", "DN", "DD",
    }
    # fmt: on

    MIN_YEAR = 1950

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IN_DRIVING_LICENCE",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = (
            replacement_pairs if replacement_pairs else [("-", ""), (" ", "")]
        )
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """Validate the matched text against known state codes and year range.

        Returns ``None`` when the state code and year are plausible (no
        checksum exists to confirm), or ``False`` when either is clearly
        invalid.
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        state_code = sanitized_value[:2].upper()
        if state_code not in self.VALID_STATE_CODES:
            return False

        year_str = sanitized_value[4:8]
        try:
            year = int(year_str)
        except ValueError:
            return False

        current_year = datetime.now().year
        if year < self.MIN_YEAR or year > current_year:
            return False

        return None
