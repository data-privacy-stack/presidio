from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DeFuehrerscheinRecognizer(PatternRecognizer):
    r"""
    Recognizes German Führerscheinnummern (driving licence numbers).

    The Führerscheinnummer is printed in field 5 of the EU card licence that
    Germany has issued since 19 January 2013. FeV Anlage 8 defines it as the
    Behördenschlüssel of the issuing authority, a sequential number assigned by
    that authority, a check digit and the number of the document issue. The
    result is an 11-character code:

        Pos 1:     Bundesland, a letter from A (Baden-Württemberg) to P (Thüringen)
        Pos 2–3:   Landkreis or kreisfreie Stadt, two digits
        Pos 4:     Office of the authority, digit or letter
        Pos 5–9:   Sequential number of the authority, base 36 ("00000" to "ZZZZZ")
        Pos 10:    Check digit, 0–9 or X
        Pos 11:    Issue number, 1–9, then A–Z

    Check digit (Bundesdruckerei, "Leitfaden zum Ausfüllen der
    Bestellunterlagen", version 9, 2013): the base-36 values of positions 1–9
    (0–9 as digits, A = 10 … Z = 35) are multiplied by 9, 8, … 1 and summed.
    The check digit is the remainder modulo 11, with a remainder of 10 written
    as X.

    Example: the official specimen licence (Musterführerschein) carries
    B072RRE2I55. B072 is the Behördenschlüssel (Bayern, Landkreis Dachau),
    RRE2I the sequential number, 5 the check digit and 5 the issue number.

    A failing check digit discards the match. A matching check digit keeps the
    pattern score instead of raising it to the maximum, because a modulo-11
    check passes for one in eleven random codes. Context words such as
    "Führerschein" raise the score.

    Pre-2013 licences (paper and laminated cards) used locally defined number
    formats and are out of scope.

    Legal basis: FeV Anlage 8 (Fahrerlaubnis-Verordnung, Muster des
    Führerscheins), Annex I to Directive 2006/126/EC (field 5).

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "de"

    PATTERNS = [
        Pattern(
            "Führerscheinnummer (EU card licence, 11 characters)",
            r"\b[A-P]\d{2}[A-Z0-9]{6}[0-9X][1-9A-Z]\b",
            0.4,
        ),
    ]

    CONTEXT = [
        "führerscheinnummer",
        "führerschein",
        "fahrerlaubnis",
        "fahrerlaubnisnummer",
        "fahrerlaubnisklasse",
        "führerscheininhaber",
        "fev",
        "kba",
        "kraftfahrt-bundesamt",
        "driving licence",
        "driving license",
        "driver's license",
        "licence number",
        "license number",
        "dokument nr",
        "dokument-nr",
        "feld 5",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "de",
        supported_entity: str = "DE_FUEHRERSCHEIN",
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
        Validate the check digit at position 10.

        :param pattern_text: the text to validate (11 characters)
        :return: False if the check digit does not match, None otherwise so the
                 pattern score and context decide the confidence.
        """
        pattern_text = pattern_text.upper()
        total = sum(
            int(character, 36) * weight
            for character, weight in zip(pattern_text[:9], range(9, 0, -1))
        )
        expected = "X" if total % 11 == 10 else str(total % 11)
        return None if pattern_text[9] == expected else False
