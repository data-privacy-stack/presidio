from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class EsCifRecognizer(PatternRecognizer):
    """
    Recognize the NIF of a Spanish legal entity (formerly CIF).

    The number has nine characters: a letter for the legal form, seven digits
    and a control character (Orden EHA/451/2008, articles 2 to 5). It may be
    written with hyphens (``B-12345674``, ``B-1234567-4``).

    The control character comes from a Luhn-style sum over the seven digits:
    digits in even positions are added as they are, digits in odd positions are
    doubled and their digits added, and the control is ``(10 - sum % 10) % 10``,
    written either as that digit or as the letter at that index of
    ``JABCDEFGHI``. Entities with keys P, Q, R, S, N and W use the letter, and
    keys A, B, E and H use the digit, unless the digits start with ``00``
    (non-resident); other keys may use either. The Orden does not publish this
    calculation; it is the one documented in the references below and used by
    validators such as python-stdnum.

    A matching control character still passes for about one in ten
    same-shaped tokens, so a valid result keeps the pattern score instead of
    being raised to full confidence, and context words raise it.

    Reference(s):
    https://www.boe.es/buscar/act.php?id=BOE-A-2008-3580
    https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/anexos/anexo-01-solicitud-nif-documentacion-aportar/informacion-sobre-numero-identificacion-fiscal/composicion-nif/personas-juridicas-entidades.html
    https://es.wikipedia.org/wiki/C%C3%B3digo_de_identificaci%C3%B3n_fiscal

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "ES_CIF (medium)",
            r"\b[ABCDEFGHJNPQRSUVW]-?[0-9]{7}-?[0-9A-J]\b",
            0.4,
        ),
    ]

    # Context is matched one lemma at a time, so phrases such as
    # "código de identificación fiscal" would never match. In the default
    # substring mode "cif" also fires on "cifra"; it only raises tokens that
    # already passed the format and control-character checks, and
    # context_matching_mode="whole_word" removes the collision.
    CONTEXT = ["cif"]

    LETTER_CONTROL_KEYS = "PQRSNW"
    DIGIT_CONTROL_KEYS = "ABEH"
    CONTROL_LETTERS = "JABCDEFGHI"

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "ES_CIF",
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

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Drop the match if its control character is wrong.

        :param pattern_text: the text detected by the pattern
        :return: False when the control character does not match, otherwise
        None so that the pattern score stands
        """
        value = pattern_text.replace("-", "").upper()
        if len(value) != 9 or not value[1:8].isdigit():
            return False
        key, digits, control = value[0], value[1:8], value[8]

        total = 0
        for position, digit in enumerate(digits, start=1):
            if position % 2 == 0:
                total += int(digit)
            else:
                total += sum(divmod(int(digit) * 2, 10))
        expected = (10 - total % 10) % 10
        expected_digit = str(expected)
        expected_letter = self.CONTROL_LETTERS[expected]

        if key in self.LETTER_CONTROL_KEYS:
            allowed = {expected_letter}
        elif key in self.DIGIT_CONTROL_KEYS and not digits.startswith("00"):
            allowed = {expected_digit}
        else:
            allowed = {expected_digit, expected_letter}

        return None if control in allowed else False
