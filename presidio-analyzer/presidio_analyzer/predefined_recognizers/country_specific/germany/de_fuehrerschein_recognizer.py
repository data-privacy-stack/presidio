from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DeFuehrerscheinRecognizer(PatternRecognizer):
    r"""
    Recognizes German Führerscheinnummern (driving license numbers).

    The Führerscheinnummer is the document number printed in Field 5 of the
    German driving license card.  Since the EU-harmonized credit-card format
    was introduced on 19 January 2013 (EU Directive 2006/126/EC, implemented
    via FeV reform), the number follows a fixed 11-character structure:

        Pos 1–2:   Behördenkürzel – 2 uppercase letters identifying the issuing
                   Fahrerlaubnisbehörde (derived from the Kfz-Zulassungskürzel
                   of the issuing Kreis/Stadt, e.g. "MU" München, "HH" Hamburg,
                   "KO" Koblenz, "BO" Bochum).  Single-letter Kfz codes such
                   as "B" (Berlin) or "K" (Köln) are used in combination as
                   2-letter authority codes here (e.g. "BO", "KN"); pure
                   single-letter + digit forms like "B0" are out of scope for
                   this strict pattern (see tests/test_de_fuehrerschein_recognizer.py).
        Pos 3–5:   Behördennummer – 3-digit authority code within the Bundesland
                   (assigned by the Kraftfahrt-Bundesamt, KBA)
        Pos 6–10:  Laufende Nummer – 5-digit sequential issue number
        Pos 11:    Prüfzeichen – 1 check character (uppercase letter A–Z or
                   digit 0–9); the derivation algorithm is not published by KBA

    Legal basis: FeV Anlage 8 (Fahrerlaubnis-Verordnung, Anlage 8 – Muster des
    Führerscheins), KBA Schlüsselverzeichnis der Fahrerlaubnisbehörden.
    EU standard: Annex I to Directive 2006/126/EC (Field 5).
    Data protection: DSGVO Art. 4 Nr. 1 (personenbezogene Daten), BDSG.

    Examples (fictitious): BO12345678A, MU12345678B, HH98765432C

    Scope note: Pre-2013 German driving licenses (pink folded card, laminated
    card) used locally defined, non-standardized number formats and remain
    legally valid until 2033 under EU grandfathering rules.  Their numbers do
    not reliably fit the 11-character pattern and are therefore out of scope
    for this recognizer.  Context words (e.g. "Führerschein", "Fahrerlaubnis")
    remain the primary means of distinguishing true license numbers from
    other 11-character alphanumeric codes.

    No checksum validation is implemented because the Prüfzeichen derivation
    formula is not published in FeV Anlage 8 or KBA administrative documents.

    Accuracy note: The pattern ``[A-Z]{2}\\d{8}[A-Z0-9]`` (11 characters) is
    fairly specific, but context words are required for high-confidence matches
    because no computable checksum is available.  The base confidence is set to
    0.35.  Formal accuracy evaluation has not been performed on a labelled dataset.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "de"

    PATTERNS = [
        Pattern(
            "Führerscheinnummer (Post-2013 EU-Format, 11 Zeichen)",
            r"\b[A-Z]{2}\d{8}[A-Z0-9]\b",
            0.35,
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
