from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class KrCrnRecognizer(PatternRecognizer):
    """
    Recognize Korean Corporate Registration Number (CRN).

    The Korean Corporate Registration Number (CRN, 법인등록번호) is a
    13-digit number assigned by the court registry office when a legal
    entity is incorporated in South Korea. It identifies the legal entity
    itself, unlike the Business Registration Number (KR_BRN) which is a
    tax identifier.

    The format is AAAABB-CCCCCCD where:
    - AAAA is the registry office code
    - BB is the corporate type code (11-15 commercial companies,
      21-22 civil-law corporations, 31-53 special-law corporations,
      71 other, 81-86 foreign corporations)
    - CCCCCC is a serial number
    - D is a check digit calculated over the preceding 12 digits

    For CRNs issued on or after January 31, 2025 (Supreme Court Rule
    No. 3173), the check digit was abolished and the last 7 digits are
    all serial digits, so the check digit validation only applies to
    CRNs issued before that date.

    Reference: Rules on assignment of registration numbers for real estate
    registration of corporations (법인 및 재외국민의 부동산등기용등록번호
    부여에 관한 규칙), https://www.law.go.kr/LSW/lsInfoP.do?lsId=005861

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes.
    :param name: The name of this recognizer
    """

    COUNTRY_CODE = "kr"

    PATTERNS = [
        Pattern(
            "CRN (Medium)",
            r"(?<!\d)\d{4}(1[1-5]|2[12]|3[1-9]|4\d|5[0-3]|71|8[1-6])(-?)\d{7}(?!\d)",
            0.5,
        )
    ]

    CONTEXT = [
        "법인등록번호",
        "법인번호",
        "법인 등록 번호",
        "등기부",
        "법인등기",
        "Korean CRN",
        "Corporate Registration Number",
        "corporation registration number",
        "CRN",
        "crn",
        "crn#",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ko",
        supported_entity: str = "KR_CRN",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = replacement_pairs if replacement_pairs else [("-", "")]

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
        Validate the pattern logic e.g., by running checksum on a detected pattern.

        This validation only applies to CRNs issued before January 31, 2025.
        CRNs issued on or after that date carry no check digit (the last
        7 digits are all serial digits), so a failed checksum does not
        prove the number invalid. Therefore, this method returns None,
        not False, when the checksum does not match.

        :param pattern_text: The text detected by the regex engine
        :return: True if the checksum matches (definitely a pre-2025 CRN),
        None otherwise
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 13 or not sanitized_value.isdigit():
            return None

        if self._validate_checksum(sanitized_value):
            return True

        return None

    @staticmethod
    def _validate_checksum(crn: str) -> bool:
        """
        Validate the check digit of a Korean Corporate Registration Number.

        The check digit is calculated by multiplying the first 12 digits
        alternately by 1 and 2, summing the products, and subtracting the
        remainder of the sum divided by 10 from 10 (modulo 10):
        check digit = (10 - (sum mod 10)) mod 10

        :param crn: The 13-digit CRN string to validate
        :return: True if the check digit matches, False otherwise
        """
        digits = [int(d) for d in crn]

        total = sum(
            digit * (1 if i % 2 == 0 else 2) for i, digit in enumerate(digits[:12])
        )
        check_digit = (10 - total % 10) % 10

        return check_digit == digits[12]
