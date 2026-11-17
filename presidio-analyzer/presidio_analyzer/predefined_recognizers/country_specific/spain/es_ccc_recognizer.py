from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class EsCccRecognizer(PatternRecognizer):
    """
    Recognize a Spanish bank account code (Código Cuenta Cliente, CCC).

    The CCC has 20 digits: bank (4), branch (4), two control digits and the
    account number (10), printed as ``EEEE OOOO DD NNNNNNNNNN``. It is the
    national part of a Spanish IBAN and still appears in older documents,
    often without the ``ES`` prefix that ``IbanRecognizer`` needs.

    Each control digit is a modulo 11 check: the first covers ``00`` followed
    by bank and branch, the second covers the account number. The digits are
    weighted 1, 2, 4, 8, 5, 10, 9, 7, 3, 6 from the left, the control digit is
    ``11 - sum % 11``, and the results 10 and 11 are written as 1 and 0. A
    random number of the same shape passes about once in a hundred tries.

    Reference(s):
    Asociación Española de Banca, "Identificación normalizada de cuentas:
    Código Cuenta Cliente (CCC) y Código Internacional de Cuenta Bancaria
    (IBAN)", serie normas y procedimientos bancarios, November 2001.
    https://es.wikipedia.org/wiki/C%C3%B3digo_cuenta_cliente

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "ES_CCC (weak)",
            r"\b[0-9]{4}([ -])[0-9]{4}\1[0-9]{2}\1[0-9]{10}\b",
            0.3,
        ),
        Pattern(
            "ES_CCC (very weak)",
            r"\b[0-9]{20}\b",
            0.05,
        ),
    ]

    WEIGHTS = (1, 2, 4, 8, 5, 10, 9, 7, 3, 6)

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "ES_CCC",
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
        :return: True when both control digits match, False otherwise
        """
        digits = "".join(c for c in pattern_text if c.isdigit())
        if len(digits) != 20:
            return False
        expected = self._control_digit("00" + digits[:8]) + self._control_digit(
            digits[10:]
        )
        return digits[8:10] == expected

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Drop all-zero placeholders, which pass the check.

        :param pattern_text: the text detected by the pattern
        :return: True when every digit is zero
        """
        return set(c for c in pattern_text if c.isdigit()) == {"0"}

    @classmethod
    def _control_digit(cls, ten_digits: str) -> str:
        total = sum(int(d) * w for d, w in zip(ten_digits, cls.WEIGHTS))
        control = 11 - total % 11
        return {10: "1", 11: "0"}.get(control, str(control))
