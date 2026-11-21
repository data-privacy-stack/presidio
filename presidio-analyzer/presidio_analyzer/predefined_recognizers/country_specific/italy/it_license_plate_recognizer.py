import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class ItLicensePlateRecognizer(PatternRecognizer):
    """
    Recognize Italian vehicle license plates (targa).

    Covers the national numbering system in use since 1994, which carries
    no reference to the province of registration:

    - Cars, trailers and other vehicles: two letters, three digits, two
      letters (``AA 999 AA``). Only 22 letters are used: I, O, Q and U are
      excluded because they can be confused with 1, 0 and V. The same
      scheme covers the reserved series for square plates (``ZA``),
      trailers (``XA``) and local police (``YA``).
    - Motorcycles: two letters followed by five digits (``AA 99999``),
      using the same 22 letters.

    Plates are matched with or without a space or hyphen between groups.
    Matching is case-sensitive, since plates are issued in capital letters:
    case-insensitive matching would flag ordinary Italian text such as
    "da 120 km" or "da 15000".
    The car pattern has a distinctive shape but no checksum, so it scores
    as medium; the motorcycle pattern is a bare letters-and-digits run and
    scores as very weak, relying on context words to be promoted.
    Not covered: pre-1994 provincial plates, mopeds, and special series
    (military, diplomatic, state bodies), whose formats are too generic
    or too varied to match reliably.

    A license plate is personal data under the GDPR when it can be linked
    to an identifiable vehicle owner.

    Sources:
    - Codice della Strada (D.Lgs. 285/1992), art. 100.
    - https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Italy

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Optional name of the recognizer
    """

    COUNTRY_CODE = "it"

    # Letters allowed on post-1994 car plates: A-Z without I, O, Q, U.
    _LETTER = "[A-HJ-NPR-TV-Z]"

    PATTERNS = [
        Pattern(
            "IT License Plate car (medium)",
            rf"\b{_LETTER}{{2}}[ -]?\d{{3}}[ -]?{_LETTER}{{2}}\b",
            0.3,
        ),
        Pattern(
            "IT License Plate motorcycle (very weak)",
            rf"\b{_LETTER}{{2}}[ -]?\d{{5}}\b",
            0.05,
        ),
    ]

    # Context matching is substring-based, so each word below also covers
    # its compounds and inflections ("targa" covers "targato", "veicolo"
    # covers "autoveicolo", "immatricola" covers "immatricolazione").
    # Short words such as "auto" or "moto" are left out on purpose: they
    # would also fire on unrelated words like "autorizzazione" or "remoto".
    CONTEXT = [
        "targa",
        "veicolo",
        "vettura",
        "automobile",
        "motociclo",
        "rimorchio",
        "immatricola",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "it",
        supported_entity: str = "IT_LICENSE_PLATE",
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
            global_regex_flags=re.DOTALL | re.MULTILINE,
        )
