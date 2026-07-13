from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class AuAbnRecognizer(PatternRecognizer):
    """
    Recognizes Australian Business Number ("ABN").

    The Australian Business Number (ABN) is a unique 11
    digit identifier issued to all entities registered in
    the Australian Business Register (ABR).
    The 11 digit ABN is structured as a 9 digit identifier
    with two leading check digits.
    The leading check digits are derived using a modulus 89 calculation.
    This recognizer identifies ABN using regex, context words and checksum.
    Reference: https://abr.business.gov.au/Help/AbnFormat

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
            "ABN (Medium)",
            r"\b\d{2}\s\d{3}\s\d{3}\s\d{3}\b",
            0.1,
        ),
        Pattern(
            "ABN (Low)",
            r"\b\d{11}\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "australian business number",
        "abn",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "AU_ABN",
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
        abn_list = [int(digit) for digit in text if not digit.isspace()]

        # Set weights based on digit position
        weight = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]

        # Perform checksums. The ABR algorithm subtracts 1 from the first
        # (left-most) digit; a leading 0 therefore becomes -1 (which makes the
        # weighted sum non-zero mod 89 and correctly fails — valid ABNs never
        # start with 0). The previous special case remapped 0 to 9, which
        # admitted some invalid leading-zero numbers as valid.
        abn_list[0] = abn_list[0] - 1
        sum_product = 0
        for i in range(11):
            sum_product += abn_list[i] * weight[i]
        remainder = sum_product % 89
        return remainder == 0
