from datetime import date
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

# Control digit weights, from Skatteetaten (the Norwegian Tax Administration):
# https://skatteetaten.github.io/folkeregisteret-api-dokumentasjon/nytt-fodselsnummer-fra-2032/
K1_WEIGHTS = (3, 7, 6, 1, 8, 9, 4, 5, 2)
K2_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)

# From 2032 the first control digit may take four values: (sum + k1) mod 11
# in {0, 1, 2, 3}. Numbers issued earlier always give 0. The issue date cannot
# be read from the number, so both rules are accepted for every number.
K1_VALID_REMAINDERS = (0, 1, 2, 3)


class NoFodselsnummerRecognizer(PatternRecognizer):
    """
    Recognizes and validates Norwegian national identity numbers.

    Covers fødselsnummer, D-nummer (day + 40), H-nummer (month + 40) and
    synthetic test numbers from Skatteetaten's Tenor (month + 80), including
    the control digit rule for numbers issued from 2032.

    Format: DDMMYY, a three-digit individual number and two mod-11 control
    digits (k1, k2), as specified by Skatteetaten (the Norwegian Tax
    Administration):
    https://skatteetaten.github.io/folkeregisteret-api-dokumentasjon/nytt-fodselsnummer-fra-2032/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "no"

    PATTERNS = [
        # A bare 11-digit run (optionally DDMMYY NNNNN): very weak on its own.
        # validate_result decides; about 0.7 % of random 11-digit runs pass
        # the date, k1 and k2 checks together.
        Pattern(
            "Norwegian fødselsnummer (very weak)",
            r"\b\d{6}[ ]?\d{5}\b",
            0.1,
        ),
    ]
    CONTEXT = [
        "fødselsnummer",
        "fødselsnr",
        "fnr",
        "personnummer",
        "personnr",
        "d-nummer",
        "dnummer",
        "national identity number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "nb",
        supported_entity: str = "NO_FODSELSNUMMER",
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

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """Validate the date part and both control digits."""
        number = pattern_text.replace(" ", "")
        if len(number) != 11 or not number.isdigit():
            return False
        digits = [int(d) for d in number]
        return self._has_valid_date(digits) and self._has_valid_control_digits(digits)

    @staticmethod
    def _has_valid_date(digits: List[int]) -> bool:
        day = digits[0] * 10 + digits[1]
        month = digits[2] * 10 + digits[3]
        year = digits[4] * 10 + digits[5]
        if day > 40:  # D-nummer
            day -= 40
        if month > 80:  # Tenor synthetic test number
            month -= 80
        elif month > 40:  # H-nummer
            month -= 40
        # From 2032 the individual number no longer encodes the century, so the
        # century is not decoded. A date valid in any possible century is
        # accepted; this still rejects impossible dates such as 30 February.
        for century in (1800, 1900, 2000):
            try:
                date(century + year, month, day)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _has_valid_control_digits(digits: List[int]) -> bool:
        k1_sum = sum(w * d for w, d in zip(K1_WEIGHTS, digits[:9])) + digits[9]
        k2_sum = sum(w * d for w, d in zip(K2_WEIGHTS, digits[:10])) + digits[10]
        return k1_sum % 11 in K1_VALID_REMAINDERS and k2_sum % 11 == 0
