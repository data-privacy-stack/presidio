from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CaPostalCodeRecognizer(PatternRecognizer):
    """Recognizes Canadian postal codes using Regex.

    Canadian postal codes follow the format `A1A 1A1` (letter-digit-letter,
    optional space, digit-letter-digit). Specific letters are excluded by
    Canada Post: D, F, I, O, Q, U are never used, and W and Z are not used
    as the first letter.

    Reference: https://en.wikipedia.org/wiki/Postal_codes_in_Canada

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ca"

    # First letter excludes D, F, I, O, Q, U (never used) and W, Z (not used
    # as the first letter); other letters exclude only D, F, I, O, Q, U.
    PATTERNS = [
        # Canonical Canada Post form with a single separating space.
        Pattern(
            "Postal code (medium)",
            r"\b"
            r"[ABCEGHJ-NPR-TVXY][0-9][ABCEGHJ-NPR-TV-Z]\s[0-9][ABCEGHJ-NPR-TV-Z][0-9]"
            r"\b",
            0.4,
        ),
        # Space omitted (common in stored data); more false-positive prone.
        Pattern(
            "Postal code (weak)",
            r"\b"
            r"[ABCEGHJ-NPR-TVXY][0-9][ABCEGHJ-NPR-TV-Z][0-9][ABCEGHJ-NPR-TV-Z][0-9]"
            r"\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "postal code",
        "postal",
        "postcode",
        "post code",
        "zip",
        "address",
        "mailing",
        "shipping",
        # French equivalents (Canada is officially bilingual)
        "code postal",
        "adresse",
        "courrier",
        "livraison",
        "expédition",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CA_POSTAL_CODE",
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
