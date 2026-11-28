import re
from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class InPanRecognizer(PatternRecognizer):
    """
    Recognizes Indian Permanent Account Number ("PAN").

    The Permanent Account Number (PAN) is a ten digit alpha-numeric code
    with the last digit being a check digit calculated using a
    modified modulus 10 calculation.
    This recognizer identifies PAN using regex and context words.

    The fourth character is the holder type (P individual, C company,
    H Hindu Undivided Family, F firm, A association of persons, T trust,
    B body of individuals, L local authority, J artificial juridical person,
    G government). A token with the exact PAN shape (five letters, four digits,
    one letter) whose fourth character is not one of these is not a PAN, and
    ``validate_result`` rejects it. It never promotes a match: no public check
    digit algorithm is used here, so valid-shape matches keep their pattern score.
    Reference: https://en.wikipedia.org/wiki/Permanent_account_number,
               https://incometaxindia.gov.in/Forms/tps/1.Permanent%20Account%20Number%20(PAN).pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "in"

    PATTERNS = [
        Pattern(
            "PAN (High)",
            r"\b([A-Za-z]{3}[AaBbCcFfGgHhJjLlPpTt]{1}[A-Za-z]{1}[0-9]{4}[A-Za-z]{1})\b",
            0.5,
        ),
        Pattern(
            "PAN (Medium)",
            r"\b([A-Za-z]{5}[0-9]{4}[A-Za-z]{1})\b",
            0.1,
        ),
        Pattern(
            "PAN (Low)",
            r"\b((?=.*?[a-zA-Z])(?=.*?[0-9]{4})[\w@#$%^?~-]{10})\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "permanent account number",
        "pan",
    ]

    HOLDER_TYPES = "ABCFGHJLPT"
    PAN_SHAPE = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IN_PAN",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = (
            replacement_pairs if replacement_pairs else [("-", ""), (" ", "")]
        )
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
        Reject PAN-shaped tokens whose holder-type character is not assigned.

        :param pattern_text: The text matched by a PAN pattern
        :return: False if the token has the exact PAN shape and an unassigned
        holder-type character; None otherwise, so the pattern score stands
        """
        sanitized = pattern_text.upper()
        for old, new in self.replacement_pairs:
            sanitized = sanitized.replace(old, new)
        if self.PAN_SHAPE.fullmatch(sanitized) is None:
            return None
        if sanitized[3] not in self.HOLDER_TYPES:
            return False
        return None
