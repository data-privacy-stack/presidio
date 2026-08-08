from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class TwNationalIdRecognizer(PatternRecognizer):
    """
    Recognize Taiwan National Identification Numbers.

    Taiwan national IDs use one leading letter followed by 9 digits.
    The second digit is typically 1 or 2, and the full value follows
    a public checksum rule defined by Taiwan's National Identification Card
    numbering scheme.

    Public references for format and verification background:
    https://www.ris.gov.tw/app/portal/188
    https://www.ris.gov.tw/app/portal/3014

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "tw"

    PATTERNS = [
        Pattern(
            "TW_NATIONAL_ID",
            r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])",
            0.3,
        ),
    ]

    CONTEXT = [
        "身分證",
        "身分證字號",
        "身份證",
        "身份證字號",
        "國民身分證",
        "national id",
        "id number",
    ]

    LETTER_MAPPING = {
        "A": 10,
        "B": 11,
        "C": 12,
        "D": 13,
        "E": 14,
        "F": 15,
        "G": 16,
        "H": 17,
        "I": 34,
        "J": 18,
        "K": 19,
        "L": 20,
        "M": 21,
        "N": 22,
        "O": 35,
        "P": 23,
        "Q": 24,
        "R": 25,
        "S": 26,
        "T": 27,
        "U": 28,
        "V": 29,
        "W": 32,
        "X": 30,
        "Y": 31,
        "Z": 33,
    }

    WEIGHTS = [1, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "zh",
        supported_entity: str = "TW_NATIONAL_ID",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = replacement_pairs if replacement_pairs else []

        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Union[bool, None]:
        """
        Validate the pattern logic by running Taiwan ID checksum verification.

        :param pattern_text: The text to validate
            (only the substring detected by the regex engine).
        :return: A bool or None, indicating whether the validation was successful.
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 10:
            return False

        if not sanitized_value[0].isalpha() or not sanitized_value[1:].isdigit():
            return False

        sanitized_value = sanitized_value.upper()

        if sanitized_value[0] not in self.LETTER_MAPPING:
            return False

        if sanitized_value[1] not in {"1", "2"}:
            return False

        return self._validate_checksum(sanitized_value)

    def _validate_checksum(self, national_id: str) -> bool:
        """Validate Taiwan National ID using the public checksum algorithm."""
        mapped_prefix = str(self.LETTER_MAPPING[national_id[0]])
        digits = [int(digit) for digit in mapped_prefix + national_id[1:]]
        checksum = sum(digit * weight for digit, weight in zip(digits, self.WEIGHTS))
        return checksum % 10 == 0
