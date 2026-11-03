import unicodedata
from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer

# Digits as written in Japanese text: half-width (0-9) and full-width (０-９).
_DIGIT = "[0-9０-９]"
# Neighbours that rule a match out: more digits, and Latin letters half- and
# full-width, so that a digit run inside a longer alphanumeric identifier
# ("SKU123456789018") is not read as a My Number. ``\b`` cannot be used:
# Japanese characters are word characters, so there is no word boundary in
# "マイナンバーは123456789018です".
_ADJACENT = "[0-9０-９A-Za-zＡ-Ｚａ-ｚ]"
_START = rf"(?<!{_ADJACENT})"
_END = rf"(?!{_ADJACENT})"


class JpMyNumberRecognizer(PatternRecognizer):
    """
    Recognize the Japanese Individual Number (My Number / マイナンバー / 個人番号).

    The Individual Number is a 12-digit number assigned to every resident
    registered in the Basic Resident Register, under the Act on the Use of
    Numbers to Identify a Specific Individual in Administrative Procedures
    (Act No. 27 of 2013). The 12th digit is a check digit over the first 11,
    defined in Article 5 of the Ordinance of the Ministry of Internal Affairs
    and Communications No. 85 of 2014:

    - Number the first 11 digits P1..P11 from the right.
    - Qn = n + 1 for 1 <= n <= 6, and Qn = n - 5 for 7 <= n <= 11.
    - r = sum(Pn * Qn) mod 11.
    - Check digit = 0 if r <= 1, otherwise 11 - r.

    Half-width and full-width digits are accepted, either contiguous or in
    4-4-4 groups with a consistent separator (``1234-5678-9018``,
    ``１２３４ ５６７８ ９０１８``).

    The check digit is mandatory, so a failing value is discarded. A passing
    value is *not* promoted to full confidence: roughly one in ten arbitrary
    12-digit runs also passes, so the pattern score stands and context words
    raise genuine matches.

    Context words are single tokens because Japanese tokenizers split
    compounds: 個人番号 becomes 個人 + 番号, and context matching compares
    against individual tokens.

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
            "JP My Number (very weak)",
            rf"{_START}{_DIGIT}{{12}}{_END}",
            0.05,
        ),
        Pattern(
            "JP My Number grouped (weak)",
            rf"{_START}{_DIGIT}{{4}}([-－ 　]){_DIGIT}{{4}}\1{_DIGIT}{{4}}{_END}",
            0.1,
        ),
    ]

    CONTEXT = [
        "マイナンバー",
        "個人",
        "mynumber",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ja",
        supported_entity: str = "JP_MY_NUMBER",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        # Applied after NFKC normalization, which maps the full-width hyphen
        # and the ideographic space to their ASCII forms.
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
        """
        Discard values whose check digit is wrong.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: False if the check digit is wrong, None otherwise.
        """
        number = self._normalize(pattern_text)
        if len(number) != 12 or not (number.isascii() and number.isdigit()):
            return False
        if self._compute_check_digit(number[:11]) != int(number[11]):
            return False
        return None

    def invalidate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Discard checksum-valid placeholders made of one repeated digit.

        ``000000000000`` passes the checksum but is never a real number.

        :param pattern_text: the text matched by the regex engine
        :return: True if the value should be discarded.
        """
        return len(set(self._normalize(pattern_text))) == 1

    def _normalize(self, pattern_text: str) -> str:
        return EntityRecognizer.sanitize_value(
            unicodedata.normalize("NFKC", pattern_text), self.replacement_pairs
        )

    @staticmethod
    def _compute_check_digit(base: str) -> int:
        """
        Compute the check digit for the first 11 digits of an Individual Number.

        :param base: the first 11 digits, left to right
        :return: the expected 12th digit
        """
        total = sum(
            int(digit) * (n + 1 if n <= 6 else n - 5)
            for n, digit in enumerate(reversed(base), start=1)
        )
        remainder = total % 11
        return 0 if remainder <= 1 else 11 - remainder
