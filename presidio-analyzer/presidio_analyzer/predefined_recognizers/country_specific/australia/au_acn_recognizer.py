from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class AuAcnRecognizer(PatternRecognizer):
    """
    Recognizes Australian Company Number ("ACN").

    The Australian Company Number (ACN) is a nine digit number
    with the last digit being a check digit calculated using a
    modified modulus 10 calculation.
    This recognizer identifies ACN using regex, context words, and checksum.
    Reference: https://asic.gov.au/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "au"

    PATTERNS = [
        Pattern(
            "ACN (Medium)",
            r"\b\d{3}\s\d{3}\s\d{3}\b",
            0.1,
        ),
        Pattern(
            "ACN (Low)",
            r"\b\d{9}\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "australian company number",
        "acn",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "AU_ACN",
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

    def validate_result(self, pattern_text: str) -> bool:
        """
        Validate the pattern logic e.g., by running checksum on a detected pattern.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: A bool indicating whether the validation was successful.
        """
        # Pre-processing before validation checks
        text = EntityRecognizer.sanitize_value(pattern_text, self.replacement_pairs)
        acn_list = [int(digit) for digit in text if not digit.isspace()]

        # Set weights based on digit position
        weight = [8, 7, 6, 5, 4, 3, 2, 1]

        # Perform checksums
        sum_product = 0
        for i in range(8):
            sum_product += acn_list[i] * weight[i]
        remainder = sum_product % 10
        # The complement must be reduced mod 10: when the weighted sum is a
        # multiple of 10 the check digit is 0, not 10. Without the outer "% 10"
        # every valid ACN whose check digit is 0 (e.g. 000000180) is rejected.
        complement = (10 - remainder) % 10
        return complement == acn_list[-1]
