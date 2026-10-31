"""Recognizer for US ICD-10-CM diagnosis codes."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UsIcd10CmRecognizer(PatternRecognizer):
    """Recognize ICD-10-CM diagnosis codes written with the decimal point.

    ICD-10-CM is the US clinical modification of the WHO classification, used
    to record diagnoses on claims and in medical records. A code has 3 to 7
    characters: the first is a letter, the second is a digit, and characters
    3 to 7 are letters or digits. A decimal point follows the third character
    when the code has more than three characters, for example ``E11.9`` or
    ``S72.001A``.

    Only the dotted form is matched, in uppercase. Besides the usual letter and
    two digits, the categories with a letter as third character (``C4A``,
    ``C7A``, ``C7B``, ``D3A``, ``M1A``, ``O9A`` and ``Z3A``) are matched; any
    other letter-third category is not. Three-character categories such as
    ``E11`` and codes written without the decimal point (``E119``, common in
    claims data) have the same shape as ordinary identifiers and are not
    detected. The pattern cannot check a code against the published code set, so
    it scores low and relies on context words to raise real codes. WHO ICD-10
    codes share the dotted shape and are matched too.

    Reference: https://www.cdc.gov/nchs/icd/icd-10-cm/index.html
    (ICD-10-CM Official Guidelines for Coding and Reporting)

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "ICD-10-CM dotted (weak)",
            # Uppercase only, even though the registry compiles patterns
            # case-insensitively: "v18.1" is a version, not a diagnosis code.
            r"(?<![\w.])(?-i:(?:[A-Z]\d{2}|C4A|C7[AB]|D3A|M1A|O9A|Z3A)\.[0-9A-Z]{1,4})"
            r"(?![\w]|\.\d)",
            0.1,
        ),
    ]

    CONTEXT = ["icd", "diagnosis"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_ICD10_CM",
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
