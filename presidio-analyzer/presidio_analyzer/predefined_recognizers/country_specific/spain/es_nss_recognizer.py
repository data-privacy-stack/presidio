from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class EsNssRecognizer(PatternRecognizer):
    """
    Recognize a Spanish social security affiliation number (NSS or NAF).

    The number has a two-digit province code, a sequence number and two
    control digits, usually written ``28/12345678/40``, ``28 12345678 40`` or
    as twelve bare digits. Older numbers have a seven-digit sequence number.

    The control digits are the remainder of dividing province and sequence
    number, read as one number, by 97. For sequence numbers below 10,000,000
    the number is ``province * 10,000,000 + sequence``, so padding an older
    seven-digit sequence to eight digits does not change the control digits.
    The Tesorería General de la Seguridad Social does not publish the
    calculation; it is the one documented in the reference below. A random
    number of the same shape passes about once in a hundred tries, and twelve
    bare digits (an order or invoice number, for example) pass at that rate
    too.

    Reference(s):
    https://www.letranif.com/formula-para-calcular-nuss-naf/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "ES_NSS (weak)",
            r"\b[0-9]{2}([/ -])[0-9]{7,8}\1[0-9]{2}\b",
            0.3,
        ),
        Pattern(
            "ES_NSS (very weak)",
            r"\b[0-9]{12}\b",
            0.05,
        ),
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "ES_NSS",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        """
        Check the two control digits.

        :param pattern_text: the text detected by the pattern
        :return: True when the control digits match, False otherwise
        """
        digits = "".join(c for c in pattern_text if c.isdigit())
        if len(digits) not in (11, 12):
            return False
        province, sequence, control = digits[:2], digits[2:-2], int(digits[-2:])

        if int(sequence) < 10_000_000:
            base = int(province) * 10_000_000 + int(sequence)
        else:
            base = int(province + sequence)
        return base % 97 == control

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Drop all-zero placeholders, which pass the check.

        :param pattern_text: the text detected by the pattern
        :return: True when every digit is zero
        """
        return set(c for c in pattern_text if c.isdigit()) == {"0"}
