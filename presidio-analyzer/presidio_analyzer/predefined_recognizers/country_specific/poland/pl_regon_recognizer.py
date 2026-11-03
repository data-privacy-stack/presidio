from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class PlRegonRecognizer(PatternRecognizer):
    """
    Recognize Polish REGON numbers using regex and checksum.

    REGON is the statistical number Statistics Poland (GUS) assigns to every
    entity in the national business register: 9 digits for a company, a sole
    trader or an institution, and 14 digits for one of its local units, whose
    first 9 digits are the parent entity's REGON.

    The last digit is a check digit: the weighted sum of the preceding digits
    modulo 11, where a remainder of 10 gives 0. The weights are
    8, 9, 2, 3, 4, 5, 6, 7 for 9 digits and 2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8
    for 14 digits, and the first 9 digits of a 14-digit number must be a valid
    REGON themselves. Statistics Poland describes the register at
    https://bip.stat.gov.pl/en/regon/ but publishes no specification of the
    check digit that we could find; the weights are those of python-stdnum
    (``stdnum.pl.regon``), which this implementation agrees with on random input.

    A bare run of 9 or 14 digits says little on its own, and 9 digits is also
    the length of a Polish phone number, so the pattern scores 0.05 and a
    failed checksum drops the match. A passing checksum does not raise the
    score: exactly one in ten 9-digit runs, and one in a hundred 14-digit runs,
    passes it.

    The context word is "regon". Context matching is substring-based by
    default, so when the recognizer is enabled for English text, "Oregon"
    raises the score as well; use ``context_matching_mode="whole_word"`` or a
    higher score threshold there.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "pl"

    PATTERNS = [
        Pattern(
            "REGON (very weak)",
            r"\b([0-9]{9}|[0-9]{14})\b",
            0.05,
        ),
    ]

    CONTEXT = ["regon"]

    WEIGHTS_9 = (8, 9, 2, 3, 4, 5, 6, 7)
    WEIGHTS_14 = (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "pl",
        supported_entity: str = "PL_REGON",
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
        Check if the REGON fails its checksum.

        :param pattern_text: The text to validate
        :return: True if invalid, False otherwise
        """
        return not self._is_valid_regon(pattern_text)

    def _is_valid_regon(self, number: str) -> bool:
        if len(number) not in (9, 14) or not number.isascii() or not number.isdigit():
            return False
        # Nine zeros pass the checksum, but they are a form placeholder, and so
        # is every 14-digit number built on them.
        if number[:9] == "000000000":
            return False
        if not self._check_digit_matches(number[:9], self.WEIGHTS_9):
            return False
        return len(number) == 9 or self._check_digit_matches(number, self.WEIGHTS_14)

    @staticmethod
    def _check_digit_matches(number: str, weights: Tuple[int, ...]) -> bool:
        weighted_sum = sum(int(digit) * w for digit, w in zip(number, weights))
        return weighted_sum % 11 % 10 == int(number[-1])
