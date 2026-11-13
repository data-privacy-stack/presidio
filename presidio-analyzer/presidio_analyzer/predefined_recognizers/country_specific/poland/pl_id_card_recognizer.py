import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class PlIdCardRecognizer(PatternRecognizer):
    """
    Recognize Polish identity card numbers using regex and checksum.

    The number of a Polish identity card (dowód osobisty) is a series of three
    letters followed by six digits, printed as ZZZ412345 and often written
    ZZZ 412345. The first digit is a check digit: with the letters counted as
    A=10 up to Z=35, the character values of ICAO Doc 9303, the nine
    characters weighted 7, 3, 1, 9, 7, 3, 1, 7, 3 must sum to a multiple of 10.
    We found no official specification of the check digit; the rule is the one
    given, with a worked example, in
    https://pl.wikipedia.org/wiki/Dow%C3%B3d_osobisty_w_Polsce. The format and
    the context phrases follow Microsoft Purview's definition:
    https://learn.microsoft.com/en-us/purview/sit-defn-poland-identity-card

    Three letters and six digits also make up invoice numbers, product codes
    and amounts such as "PLN 100000", so the pattern scores 0.1 and a failed
    checksum drops the match. A passing checksum does not raise the score: one
    in ten arbitrary tokens of this shape passes it. The series is matched in
    any case when it touches the digits, but must be in capitals when a space
    separates them, which keeps prose such as "dla 400000" out. The form
    "seria ZZZ nr 412345", with words between series and number, is not
    matched.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "pl"

    PATTERNS = [
        Pattern(
            "Polish ID card (weak)",
            r"\b(?:[A-Z]{3}[0-9]{6}|(?-i:[A-Z]{3})[  ][0-9]{6})\b",
            0.1,
        ),
    ]

    # On its own, "dowód" is any proof or receipt ("dowód zakupu", "dowód
    # księgowy"), so the context is the full name of the document. Its case
    # forms are listed so that whole-word matching, and an NLP engine without
    # Polish lemmas, find them too.
    CONTEXT = [
        "dowód osobisty",
        "dowod osobisty",
        "dowodu osobistego",
        "dowodem osobistym",
        "dowodzie osobistym",
        "dowód tożsamości",
        "dowodu tożsamości",
        "dokumentu tożsamości",
        "dow. os.",
        "seria i numer",
        "identity card",
        "id card",
    ]

    WEIGHTS = (7, 3, 1, 9, 7, 3, 1, 7, 3)

    # The worked example of the check digit in the Polish Wikipedia article,
    # widely copied as a sample, and a number that article notes was never
    # issued. Both pass the checksum.
    SAMPLE_NUMBERS = frozenset({"ABA300000", "AAA000000"})

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "pl",
        supported_entity: str = "PL_ID_CARD",
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the identity card number fails its checksum or is a sample.

        :param pattern_text: The text to validate
        :return: True if invalid, False otherwise
        """
        number = pattern_text.replace(" ", "").replace(" ", "")
        # Case-insensitive [A-Z] also matches the dotless i, the long s and the
        # Kelvin sign, which upper() would turn into ASCII letters.
        if not number.isascii():
            return True
        number = number.upper()
        if number in self.SAMPLE_NUMBERS:
            return True
        return not self._is_valid_checksum(number)

    def _is_valid_checksum(self, number: str) -> bool:
        if not re.fullmatch(r"[A-Z]{3}[0-9]{6}", number):
            return False
        values = [ord(letter) - ord("A") + 10 for letter in number[:3]]
        values += [int(digit) for digit in number[3:]]
        weighted_sum = sum(value * w for value, w in zip(values, self.WEIGHTS))
        return weighted_sum % 10 == 0
