from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DateRecognizer(PatternRecognizer):
    """
    Recognize date using regex.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    PATTERNS = [
        Pattern(
            "Datetime (yyyy-mm-ddThh:mm[:ss[.f]] with timezone)",
            r"\b(?:(\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T[0-2]\d:[0-5]\d:[0-5]\d\.\d+([+-][0-2]\d:[0-5]\d|Z))|(\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T[0-2]\d:[0-5]\d:[0-5]\d([+-][0-2]\d:[0-5]\d|Z))|(\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T[0-2]\d:[0-5]\d([+-][0-2]\d:[0-5]\d|Z)))\b",
            0.8,
        ),
        Pattern(
            "mm/dd/yyyy or mm/dd/yy",
            r"\b(([1-9]|0[1-9]|1[0-2])/([1-9]|0[1-9]|[1-2][0-9]|3[0-1])/(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "dd/mm/yyyy or dd/mm/yy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])/([1-9]|0[1-9]|1[0-2])/(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "yyyy/mm/dd",
            r"\b(\d{4}/([1-9]|0[1-9]|1[0-2])/([1-9]|0[1-9]|[1-2][0-9]|3[0-1]))\b",
            0.6,
        ),
        Pattern(
            "mm-dd-yyyy",
            r"\b(([1-9]|0[1-9]|1[0-2])-([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-\d{4})\b",
            0.6,
        ),
        Pattern(
            "dd-mm-yyyy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-([1-9]|0[1-9]|1[0-2])-\d{4})\b",
            0.6,
        ),
        Pattern(
            "yyyy-mm-dd",
            r"\b(\d{4}-([1-9]|0[1-9]|1[0-2])-([1-9]|0[1-9]|[1-2][0-9]|3[0-1]))\b",
            0.6,
        ),
        Pattern(
            "dd.mm.yyyy or dd.mm.yy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])\.([1-9]|0[1-9]|1[0-2])\.(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "dd-MMM-yyyy or dd-MMM-yy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "MMM-yyyy or MMM-yy",
            r"\b((JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "dd-MMM or dd-MMM",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))\b",
            0.6,
        ),
        Pattern(
            "mm/yyyy or m/yyyy",
            r"\b(([1-9]|0[1-9]|1[0-2])/\d{4})\b",
            0.2,
        ),
        Pattern(
            "mm/yy or m/yy",
            r"\b(([1-9]|0[1-9]|1[0-2])/\d{2})\b",
            0.1,
        ),
    ]

    CONTEXT = ["date", "birthday"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "DATE_TIME",
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
