from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class FrRibRecognizer(PatternRecognizer):
    """
    Recognize a French RIB (Relevé d'Identité Bancaire) using regex and checksum.

    A RIB is the domestic French bank account identifier. It has 23 characters:
    bank code (5 digits), branch code (5 digits), account number (11
    alphanumeric characters) and a 2-digit key. The groups may be separated by
    single spaces. The IBAN of a French account contains the same 23
    characters after "FR" and two check digits, but it is grouped differently
    and is covered by the generic IBAN_CODE recognizer.

    The key is 97 - ((89 * bank + 15 * branch + 3 * account) mod 97), where
    the letters of the account number are first replaced by digits (A-I map to
    1-9, J-R to 1-9, S-Z to 2-9).
    See https://fr.wikipedia.org/wiki/Relev%C3%A9_d%27identit%C3%A9_bancaire

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "fr"

    PATTERNS = [
        Pattern(
            "FR_RIB",
            r"\b\d{5} ?\d{5} ?[0-9A-Za-z]{11} ?\d{2}\b",
            0.3,
        ),
    ]

    CONTEXT = ["rib", "iban", "bancaire", "banque", "compte", "bank", "account"]

    _LETTER_TO_DIGIT = {
        **{c: str(i % 9 + 1) for i, c in enumerate("ABCDEFGHI")},
        **{c: str(i % 9 + 1) for i, c in enumerate("JKLMNOPQR")},
        **{c: str(i % 8 + 2) for i, c in enumerate("STUVWXYZ")},
    }

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "fr",
        supported_entity: str = "FR_RIB",
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

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        rib = pattern_text.replace(" ", "").upper()
        if len(rib) != 23 or not rib[:10].isdigit() or not rib[21:].isdigit():
            return False

        account = "".join(self._LETTER_TO_DIGIT.get(c, c) for c in rib[10:21])
        if not account.isdigit():
            return False

        weighted = 89 * int(rib[:5]) + 15 * int(rib[5:10]) + 3 * int(account)
        return int(rib[21:]) == 97 - weighted % 97
