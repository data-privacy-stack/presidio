from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer

from .digits import DIGIT_CLASS


class InAadhaarRecognizer(PatternRecognizer):
    """
    Recognizes Indian UIDAI Person Identification Number ("AADHAAR").

    Reference: https://en.wikipedia.org/wiki/Aadhaar
    A 12 digit unique number that is issued to each individual by Government of India
    The last digit is a Verhoeff checksum of the preceding eleven digits.
    The digits are matched in ASCII and in the nine Indic digit blocks, since
    Indian-language text writes the same number in the script it is written in.
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
            "AADHAAR (Very Weak)",
            rf"\b{DIGIT_CLASS}{{12}}\b",
            0.01,
        ),
        Pattern(
            "AADHAR (Very Weak)",
            rf"\b{DIGIT_CLASS}{{4}}[- :]{DIGIT_CLASS}{{4}}[- :]{DIGIT_CLASS}{{4}}\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "aadhaar",
        "uidai",
    ]

    utils = None

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IN_AADHAAR",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ) -> None:
        self.replacement_pairs = (
            replacement_pairs
            if replacement_pairs
            else [("-", ""), (" ", ""), (":", "")]
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
        """Determine absolute value based on calculation."""
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        return self.__check_aadhaar(sanitized_value)

    def __check_aadhaar(self, sanitized_value: str) -> bool:
        is_valid_aadhaar: bool = False
        if (
            len(sanitized_value) == 12
            and sanitized_value.isnumeric() is True
            and int(sanitized_value[0]) >= 2
            and self._is_verhoeff_number(int(sanitized_value)) is True
            and self._is_palindrome(sanitized_value) is False
        ):
            is_valid_aadhaar = True
        return is_valid_aadhaar

    @staticmethod
    def _is_palindrome(text: str, case_insensitive: bool = False) -> bool:
        """
        Validate if input text is a true palindrome.

        :param text: input text string to check for palindrome
        :param case_insensitive: optional flag to check palindrome with no case
        :return: True / False
        """
        palindrome_text = text
        if case_insensitive:
            palindrome_text = palindrome_text.replace(" ", "").lower()
        return palindrome_text == palindrome_text[::-1]

    @staticmethod
    def _is_verhoeff_number(input_number: int) -> bool:
        """
        Check if the input number is a true verhoeff number.

        :param input_number:
        :return:
        """
        __d__ = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        ]
        __p__ = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
            [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
            [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
            [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
            [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
            [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
            [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
        ]
        __inv__ = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

        c = 0
        inverted_number = list(map(int, reversed(str(input_number))))
        for i in range(len(inverted_number)):
            c = __d__[c][__p__[i % 8][inverted_number[i]]]
        return __inv__[c] == 0
