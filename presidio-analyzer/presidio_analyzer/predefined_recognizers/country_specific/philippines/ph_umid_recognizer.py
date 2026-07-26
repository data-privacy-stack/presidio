from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class PhUmidRecognizer(PatternRecognizer):
    """
    Recognize PH UMID number using regex.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ph"

    PATTERNS = [
        Pattern("UMID (with dashes)", r"\b\d{4}-\d{7}-\d\b", 0.5),
        Pattern("UMID (without dashes)", r"\b\d{12}\b", 0.3),
    ]

    CONTEXT = [
        "umid",
        "unified multi-purpose id",
        "crn",
        "common reference number",
        "sss",
        "gsis",
        "philhealth",
        "pag-ibig",
        "umid number",
        "umid card",
        "unified multipurpose id",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "PH_UMID",
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
