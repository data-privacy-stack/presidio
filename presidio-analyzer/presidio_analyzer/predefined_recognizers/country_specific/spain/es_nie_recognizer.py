from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class EsNieRecognizer(PatternRecognizer):
    """
    Recognize NIE number using regex and checksum.

    Reference(s):
    https://es.wikipedia.org/wiki/N%C3%BAmero_de_identidad_de_extranjero
    https://www.interior.gob.es/opencms/ca/servicios-al-ciudadano/tramites-y-gestiones/dni/calculo-del-digito-de-control-del-nif-nie/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes
    or spaces.
    """

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "NIE",
            r"\b[X-Z]?[0-9]?[0-9]{7}[-]?[A-Z]\b",
            0.5,
        ),
    ]

    CONTEXT = ["número de identificación de extranjero", "NIE"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "ES_NIE",
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

    def validate_result(self, pattern_text: str) -> bool:
        """Validate the pattern by using the control character."""

        pattern_text = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        ).upper()

        letters = "TRWAGMYFPDXBNJZSQVHLCKE"
        letter = pattern_text[-1]

        # check last is a letter, and first is in X,Y,Z
        if not pattern_text[1:-1].isdigit() or pattern_text[:1] not in "XYZ":
            return False
        # check size is 8 or 9
        if len(pattern_text) < 8 or len(pattern_text) > 9:
            return False

        # replace XYZ with 012, and check the mod 23
        number = int(str("XYZ".index(pattern_text[0])) + pattern_text[1:-1])
        return letter == letters[number % 23]
