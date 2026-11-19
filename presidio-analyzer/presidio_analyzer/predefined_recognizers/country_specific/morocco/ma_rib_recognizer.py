from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class MaRibRecognizer(PatternRecognizer):
    """
    Recognize the Moroccan bank account identifier (RIB).

    The RIB (Relevé d'Identité Bancaire) is the 24-digit account identifier
    used by every bank in Morocco: a 3-digit bank code, a 3-digit locality
    code, a 16-digit account number and a 2-digit key. Structure: U.S. Social
    Security Administration, POMS GN 02402.297, "Coding Morocco Bank Data on
    the Master Beneficiary Record",
    https://secure.ssa.gov/poms.nsf/lnx/0202402297.

    The key makes the 24-digit number divisible by 97. No official text
    spells this rule out; it holds for the RIB that Bank Al-Maghrib published
    for the special fund no. 126. About one random 24-digit number in 97
    also passes, so the key only removes candidates: a number that fails is
    dropped, one that passes keeps the pattern score and can be raised by
    context words.

    The digits are written in one run or in groups. Banks group the account
    number in different ways, so a grouped number is matched when the bank
    code and the locality code are groups of three and every group is
    separated by the same character: a space, a dot or a hyphen. It is skipped
    when another group of digits stands right before or after it. A separate
    number written right after a shorter one, with the same separator, cannot
    be told apart from a key, so the grouped form gets a lower score.

    The label "RIB" is not a default context word, because context words are
    matched as substrings and it is part of common French words. Pass it in
    ``context`` when the context enhancer matches whole words.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: The name of this recognizer
    """

    COUNTRY_CODE = "ma"

    PATTERNS = [
        Pattern("RIB (weak)", r"\b[0-9]{24}\b", 0.3),
        Pattern(
            "RIB in groups (weak)",
            r"\b(?<!\d[ .-])"
            r"[0-9]{3}([ .-])[0-9]{3}\1(?:[0-9]\1?){17}[0-9]"
            r"\b(?![ .-]?\d)",
            0.2,
        ),
    ]

    CONTEXT = [
        "bancaire",
        "banque",
        "virement",
        "بنكي",
    ]

    SEPARATORS = str.maketrans("", "", " .-")

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ar",
        supported_entity: str = "MA_RIB",
        name: Optional[str] = None,
    ) -> None:
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
        Drop a number whose key is wrong.

        :param pattern_text: The text matched by the pattern
        :return: False if the 24 digits are not divisible by 97, None otherwise
        """
        if int(self._digits(pattern_text)) % 97 != 0:
            return False
        return None

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Reject a number whose bank, locality and account digits are all zero.

        :param pattern_text: The text matched by the pattern
        :return: True if the 22 digits before the key are all zero
        """
        return int(self._digits(pattern_text)[:22]) == 0

    def _digits(self, pattern_text: str) -> str:
        return pattern_text.translate(self.SEPARATORS)
