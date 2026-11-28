"""Mask some or all given text entity PII with given character."""

from typing import Dict

from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.operators import Operator, OperatorType
from presidio_anonymizer.services.validators import (
    _get_bad_typed_parameter_error_message,
    validate_parameter,
)


class Mask(Operator):
    """Mask the given text with given value."""

    CHARS_TO_MASK = "chars_to_mask"
    FROM_END = "from_end"
    MASKING_CHAR = "masking_char"

    def operate(self, text: str = None, params: Dict = None) -> str:
        """
        Mask a given amount of text with a given character.

        :param text: the text to be masked
        :param params:
            masking_char: The character to be masked with
            chars_to_mask: The amount of characters to mask
            from_end: Whether to mask the text from it's end
        :return: the masked text
        """
        effective_chars_to_mask = self._get_effective_chars_to_mask(
            text, params.get(self.CHARS_TO_MASK)
        )
        from_end = params.get(self.FROM_END)
        masking_char = params.get(self.MASKING_CHAR)
        return self._get_anonymized_text(
            text, effective_chars_to_mask, from_end, masking_char
        )

    def validate(self, params: Dict = None) -> None:
        """
        Validate the parameters for mask.

        :param params:
            masking_char: The character to be masked with
            chars_to_mask: The amount of characters to mask
            from_end: Whether to mask the text from it's end
        """
        masking_char = params.get(self.MASKING_CHAR)
        validate_parameter(masking_char, self.MASKING_CHAR, str)
        if not isinstance(masking_char, str) or len(masking_char) != 1:
            raise InvalidParamError(
                f"Invalid input, {self.MASKING_CHAR} must be a character"
            )

        chars_to_mask = params.get(self.CHARS_TO_MASK)
        validate_parameter(chars_to_mask, self.CHARS_TO_MASK, int)
        # validate_parameter skips the type check for falsy values such as ""
        # or [], which would otherwise fail later in operate() with a TypeError.
        if not isinstance(chars_to_mask, int):
            raise InvalidParamError(
                _get_bad_typed_parameter_error_message(
                    self.CHARS_TO_MASK,
                    expected_type=int,
                    actual_type=type(chars_to_mask),
                )
            )
        validate_parameter(params.get(self.FROM_END), self.FROM_END, bool)

    def operator_name(self) -> str:
        """Return operator name."""
        return "mask"

    def operator_type(self) -> OperatorType:
        """Return operator type."""
        return OperatorType.Anonymize

    @staticmethod
    def _get_effective_chars_to_mask(text, chars_to_mask):
        return min(len(text), chars_to_mask) if chars_to_mask > 0 else 0

    @staticmethod
    def _get_anonymized_text(text, chars_to_mask, from_end, masking_char):
        if not from_end:
            return masking_char * chars_to_mask + text[chars_to_mask:]
        else:
            mask_from_index = len(text) - chars_to_mask
            return text[:mask_from_index] + masking_char * chars_to_mask
