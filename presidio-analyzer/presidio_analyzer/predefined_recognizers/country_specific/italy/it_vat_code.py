from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class ItVatCodeRecognizer(PatternRecognizer):
    """
    Recognizes Italian VAT code using regex and checksum.

    For more information about italian VAT code:
        https://en.wikipedia.org/wiki/VAT_identification_number#:~:text=%5B2%5D)-,Italy,-Partita%20IVA

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "it"

    # Class variables
    PATTERNS = [
        Pattern(
            "IT Vat code (piva)",
            r"\b[0-9](?:[ _]?[0-9]){10}\b",
            0.1,
        )
    ]

    CONTEXT = ["piva", "partita iva", "pi"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "it",
        supported_entity: str = "IT_VAT_CODE",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
        version: str = "0.0.1",
    ):
        self.replacement_pairs = (
            replacement_pairs
            if replacement_pairs
            else [("-", ""), (" ", ""), ("_", "")]
        )
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
            version=version,
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

        # Edge-case that passes the checksum even though it is not a
        # valid italian vat code.
        if text == "00000000000":
            return False

        x = 0
        y = 0

        for i in range(0, 5):
            x += int(text[2 * i])
            tmp_y = int(text[2 * i + 1]) * 2
            if tmp_y > 9:
                tmp_y = tmp_y - 9
            y += tmp_y

        t = (x + y) % 10
        c = (10 - t) % 10

        if c == int(text[10]):
            result = True
        else:
            result = False

        return result
