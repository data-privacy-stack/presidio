from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class TrTaxIdRecognizer(PatternRecognizer):
    """
    Recognize Turkish Tax Identification Number (Vergi Kimlik Numarası / VKN).

    The Turkish Tax Identification Number (VKN) is a 10-digit number assigned to
    corporations, partnerships, and individual taxpayers by the Turkish Revenue
    Administration (Gelir İdaresi Başkanlığı - GİB).

    Official specification:
    - Legal basis: Vergi Kimlik Numarası Genel Tebliği (Sıra No: 2),
      published in Resmi Gazete No: 23793 on 21.08.1999.
    - Format: Exactly 10 digits.
    - Checksum algorithm (GİB Modulo-10):
      For the first 9 digits d_0 ... d_8 with weights i = 9 - k (k from 0 to 8):
        c1 = (d_k + i) % 10
        c2 = (c1 * (2 ** i)) % 9 (if c1 != 0 and (c1 * 2^i) % 9 == 0, then c2 = 9;
             if c1 == 0, then c2 = 0)
        total = sum(c2 for k in 0..8)
        check_digit = (10 - (total % 10)) % 10
      The 10th digit d_9 must equal check_digit.

    Validation and scoring policy:
    - ``validate_result`` verifies syntactic format (10 digits) and the official
      GİB Modulo-10 checksum. Inputs failing the checksum return ``False`` and
      are dropped.
    - Because a Modulo-10 check passes ~10% of arbitrary 10-digit numbers by
      chance and cannot prove live assignment in GİB databases, passing the
      checksum returns ``None`` rather than ``True``. This preserves the base
      pattern score (0.3) for bare numbers and relies on surrounding context
      words (via ``ContextAwareEnhancer``) to boost confidence.
    - ``invalidate_result`` filters dummy repeated sequences (e.g. 4444444444,
      0000000000).

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "tr"

    PATTERNS = [
        Pattern(
            "TR_TAX_ID (weak)",
            r"\b[0-9]{10}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "vergi kimlik",
        "vergi kimlik no",
        "vergi kimlik numarası",
        "vergi no",
        "vergi numarası",
        "vkn",
        "tax id",
        "tax number",
        "vergi dairesi",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "tr",
        supported_entity: str = "TR_TAX_ID",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = replacement_pairs if replacement_pairs else []

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
        Validate the pattern logic by running the GİB Modulo-10 checksum.

        Returns ``False`` if the candidate is malformed or fails the checksum,
        discarding the match. Returns ``None`` when the checksum succeeds so
        that the base pattern score (0.3) is preserved and final confidence is
        driven by surrounding context words rather than jumping to 1.0.

        :param pattern_text: the text to validate.
        Only the part in text that was detected by the regex engine
        :return: False if invalid, None if checksum passes.
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 10 or not sanitized_value.isdigit():
            return False

        if not self._validate_checksum(sanitized_value):
            return False

        return None

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text is a dummy repeated sequence.

        :param pattern_text: Text detected by pattern matching
        :return: True if invalidated, False otherwise
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        if len(set(sanitized_value)) <= 1:
            return True
        return False

    def _validate_checksum(self, vkn: str) -> bool:
        """
        Validate Turkish Tax ID using the official GİB Modulo-10 checksum algorithm.

        :param vkn: 10-digit VKN string
        :return: True if valid, False otherwise
        """
        digits = [int(d) for d in vkn]
        total = 0
        for k in range(9):
            i = 9 - k
            c1 = (digits[k] + i) % 10
            if c1 != 0:
                c2 = (c1 * (2 ** i)) % 9
                if c2 == 0:
                    c2 = 9
            else:
                c2 = 0
            total += c2

        check_digit = (10 - (total % 10)) % 10
        return check_digit == digits[9]
