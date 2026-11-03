from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class TrNationalIdRecognizer(PatternRecognizer):
    """
    Recognize Turkish National Identification Number (TC Kimlik No / TCKN).

    The Turkish National ID is an 11-digit number where:
    - First digit cannot be 0
    - 10th digit = (sum_of_odd_positions * 7 - sum_of_even_positions) % 10
    - 11th digit = (sum of first 10 digits) % 10

    Checksum validation based on the official Nüfus ve Vatandaşlık İşleri
    Genel Müdürlüğü (NVI) algorithm, referenced in KVKK compliance guidelines.
    See: https://tckimlik.nvi.gov.tr/ (NVİ official service portal)

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "tr"

    DEFAULT_REPLACEMENT_PAIRS = [
        ("-", ""),
        (" ", ""),
        (",", ""),
    ]

    PATTERNS = [
        Pattern(
            "TR_NATIONAL_ID",
            r"\b[1-9][0-9]{10}\b",
            0.3,
        ),
        Pattern(
            "TR_NATIONAL_ID (delimited)",
            r"(?<![0-9][ ,-])(?<![0-9], )\b(?:"
            r"[1-9][0-9]{2}(?:(?:[ -]|, ?)[0-9]{3}){2}(?:[ -]|, ?)[0-9]{2}"
            r"|[1-9][0-9]{2}(?:(?:[ -]|, ?)[0-9]{2}){4}"
            r"|[1-9][0-9]{3}(?:[ -]|, ?)[0-9]{4}(?:[ -]|, ?)[0-9]{3}"
            r")\b(?!(?:[ -]|, ?)[0-9])",
            0.3,
        ),
    ]

    CONTEXT = [
        "tc kimlik",
        "kimlik no",
        "kimlik numarası",
        "tckn",
        "tc no",
        "nüfus cüzdanı",
        "national id",
        "turkish id",
        "türk kimlik",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "tr",
        supported_entity: str = "TR_NATIONAL_ID",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = (
            replacement_pairs
            if replacement_pairs is not None
            else self.DEFAULT_REPLACEMENT_PAIRS
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

    def validate_result(self, pattern_text: str) -> Union[bool, None]:
        """
        Validate the pattern logic by running checksum on a detected pattern.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: A bool or None, indicating whether the validation was successful.
        """
        if self._has_inconsistent_delimiters(pattern_text):
            return False

        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 11 or not sanitized_value.isdigit():
            return False

        if sanitized_value[0] == "0":
            return False

        if len(set(sanitized_value[:10])) == 1:
            return False

        return self._validate_checksum(sanitized_value)

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be validated as a TR_NATIONAL_ID entity.

        Rejects mismatched delimiters and dummy repeated-digit sequences
        (e.g. 11111111110) that mathematically satisfy the modulo checksum.

        :param pattern_text: Text detected as pattern by regex.
        :return: True if invalidated, False otherwise.
        """
        if self._has_inconsistent_delimiters(pattern_text):
            return True

        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        if len(sanitized_value) == 11 and sanitized_value.isdigit():
            if len(set(sanitized_value[:10])) == 1:
                return True

        return False

    @staticmethod
    def _has_inconsistent_delimiters(pattern_text: str) -> bool:
        has_hyphen = "-" in pattern_text
        has_space = " " in pattern_text
        has_comma = "," in pattern_text

        if has_hyphen and (has_space or has_comma):
            return True

        if has_comma and has_space:
            if pattern_text.count(",") != pattern_text.count(", "):
                return True

        return False

    def _validate_checksum(self, tckn: str) -> bool:
        """
        Validate Turkish National ID using the official NVI checksum algorithm.

        :param tckn: The TCKN to validate
        :return: True if checksum is valid, False otherwise
        """
        digits = [int(d) for d in tckn]

        odd_sum = sum(digits[i] for i in range(0, 9, 2))
        even_sum = sum(digits[i] for i in range(1, 8, 2))

        tenth = (odd_sum * 7 - even_sum) % 10
        if tenth != digits[9]:
            return False

        eleventh = sum(digits[:10]) % 10
        if eleventh != digits[10]:
            return False

        return True
