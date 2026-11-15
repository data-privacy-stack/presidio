import unicodedata
from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer

# Digits as written in Japanese text: half-width (0-9) and full-width (０-９).
_DIGIT = "[0-9０-９]"
# Neighbours that rule a match out: more digits, and Latin letters half- and
# full-width, so that a digit run inside a longer alphanumeric identifier
# ("T7000012050002AB") is not read as a Corporate Number. ``\b`` cannot be
# used next to Japanese characters, which are word characters.
_ADJACENT = "[0-9０-９A-Za-zＡ-Ｚａ-ｚ]"
_START = rf"(?<!{_ADJACENT})"
_END = rf"(?!{_ADJACENT})"


class JpCorporateNumberRecognizer(PatternRecognizer):
    """
    Recognize the Japanese Corporate Number (法人番号).

    The Corporate Number is a 13-digit number designated by the National Tax
    Agency under Article 39 of the Act on the Use of Numbers to Identify a
    Specific Individual in Administrative Procedures (Act No. 27 of 2013).
    The *first* digit is a check digit over the other 12, defined in Article 2
    of the Ordinance of the Ministry of Finance No. 70 of 2014:

    - Number the 12 base digits P1..P12 from the right.
    - Qn = 1 if n is odd, 2 if n is even.
    - Check digit = 9 - (sum(Pn * Qn) mod 9).

    The registration number of a corporate Qualified Invoice Issuer
    (適格請求書発行事業者登録番号) is ``T`` followed by the Corporate Number;
    that prefix makes the format distinctive and gets its own pattern.

    The check digit is mandatory, so a failing value is discarded. A passing
    value is not promoted to full confidence, because about one in nine
    arbitrary 13-digit runs also passes.

    Corporate Numbers are published by law and identify legal entities, not
    individuals. This recognizer is for deployments that must mask them anyway.

    Context words are single tokens because Japanese tokenizers split
    compounds: 法人番号 becomes 法人 + 番号.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    :param name: Name of this recognizer
    """

    COUNTRY_CODE = "jp"

    PATTERNS = [
        Pattern(
            "JP Corporate Number (very weak)",
            rf"{_START}{_DIGIT}{{13}}{_END}",
            0.05,
        ),
        Pattern(
            "JP Qualified Invoice Issuer Number (medium)",
            rf"{_START}[TＴ]{_DIGIT}{{13}}{_END}",
            0.3,
        ),
    ]

    CONTEXT = [
        "法人",
        "インボイス",
        "corporate",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ja",
        supported_entity: str = "JP_CORPORATE_NUMBER",
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

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Discard values whose check digit is wrong.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: False if the check digit is wrong, None otherwise.
        """
        number = self._normalize(pattern_text)
        if len(number) != 13 or not (number.isascii() and number.isdigit()):
            return False
        if self._compute_check_digit(number[1:]) != int(number[0]):
            return False
        return None

    def invalidate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Discard checksum-valid placeholders whose base digits are all the same.

        :param pattern_text: the text matched by the regex engine
        :return: True if the value should be discarded.
        """
        return len(set(self._normalize(pattern_text)[1:])) == 1

    def _normalize(self, pattern_text: str) -> str:
        number = unicodedata.normalize("NFKC", pattern_text).upper()
        number = EntityRecognizer.sanitize_value(number, self.replacement_pairs)
        return number[1:] if number.startswith("T") else number

    @staticmethod
    def _compute_check_digit(base: str) -> int:
        """
        Compute the check digit for the 12 base digits of a Corporate Number.

        :param base: digits 2-13 of the Corporate Number, left to right
        :return: the expected first digit
        """
        total = sum(
            int(digit) * (1 if n % 2 else 2)
            for n, digit in enumerate(reversed(base), start=1)
        )
        return 9 - (total % 9)
