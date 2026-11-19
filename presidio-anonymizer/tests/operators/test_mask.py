import pytest

from presidio_anonymizer.operators import Mask
from presidio_anonymizer.entities import InvalidParamError


@pytest.mark.parametrize(
    # fmt: off
    "text, masking_char, chars_to_mask, from_end, anonymized_text",
    [
        ("text", "*", 4, False, "****"),  # Fully mask
        ("text", "*", 4, True, "****"),  # Fully mask from the end
        ("text", "*", 3, False, "***t"),  # Partially mask
        ("text", "*", 3, True, "t***"),  # Partially mask from the end
        ("text", "*", 5, False, "****"),  # Fully mask with overflowing chars_to_mask
        ("text", "*", 5, True, "****"),  # from the end
        ("t", "*", 1, False, "*"),  # Fully mask one character text
        ("t", "*", 1, True, "*"),  # from the end
        ("t", "*", 3, False, "*"),  # with overflowing chars_to_mask
        ("t", "*", 3, True, "*"),  # from the end
        ("text", "😈", 4, False, "😈😈😈😈"),  # Mask with 'Unicode EmojiSources' character
        ("😈😈😈😈", "*", 4, False, "****"),  # Mask 'Unicode EmojiSources' character
        ("text", "*", 0, False, "text"),  # Nullified mask
        ("text", "*", 0, True, "text"),  # from the end
        ("text", "*", -1, False, "text"),  # Negative chars_to_mask
        ("text", "*", -1, True, "text"),  # from the end
        ("", "*", 1, False, ""),  # Empty string
        ("", "*", 0, False, ""),  # Empty string nullified mask
    ]
    # fmt: on
)
def test_when_given_valid_value_then_expected_string_returned(
    text, masking_char, chars_to_mask, from_end, anonymized_text
):
    params = {
        "masking_char": masking_char,
        "chars_to_mask": chars_to_mask,
        "from_end": from_end,
    }

    actual_anonymized_text = Mask().operate(text=text, params=params)

    assert anonymized_text == actual_anonymized_text


def test_when_masking_char_is_missing_then_ipe_raised():
    params = _get_default_mask_parameters()
    params.pop("masking_char")

    with pytest.raises(InvalidParamError, match="Expected parameter masking_char"):
        Mask().validate(params)


def test_when_masking_char_is_bad_typed_then_ipe_raised():
    params = _get_default_mask_parameters()
    params["masking_char"] = 1

    with pytest.raises(
        InvalidParamError,
        match="Invalid parameter value for masking_char. "
        "Expecting 'string', but got 'number'.",
    ):
        Mask().validate(params)


def test_when_masking_char_length_is_greater_than_one_then_ipe_raised():
    params = _get_default_mask_parameters()
    params["masking_char"] = "string_not_character"

    with pytest.raises(
        InvalidParamError, match="Invalid input, masking_char must be a character"
    ):
        Mask().validate(params)


def test_when_masking_char_is_empty_then_ipe_raised():
    params = _get_default_mask_parameters()
    params["masking_char"] = ""

    with pytest.raises(
        InvalidParamError, match="Invalid input, masking_char must be a character"
    ):
        Mask().validate(params)


def test_when_chars_to_mask_is_missing_then_ipe_raised():
    params = _get_default_mask_parameters()
    params.pop("chars_to_mask")

    with pytest.raises(InvalidParamError, match="Expected parameter chars_to_mask"):
        Mask().validate(params)


def test_when_chars_to_mask_bad_typed_then_ipe_raised():
    params = _get_default_mask_parameters()
    params["chars_to_mask"] = "not_an_integer"

    with pytest.raises(
        InvalidParamError,
        match="Invalid parameter value for chars_to_mask. "
        "Expecting 'number', but got 'string'.",
    ):
        Mask().validate(params)


def test_when_from_end_is_missing_then_ipe_raised():
    params = _get_default_mask_parameters()
    params.pop("from_end")

    with pytest.raises(InvalidParamError, match="Expected parameter from_end"):
        Mask().validate(params)


def test_when_from_end_is_bad_typed_then_ipe_raised():
    params = _get_default_mask_parameters()
    params["from_end"] = "not_a_boolean"

    with pytest.raises(
        InvalidParamError,
        match="Invalid parameter value for from_end. "
        "Expecting 'boolean', but got 'string'.",
    ):
        Mask().validate(params)


def _get_default_mask_parameters():
    return {"masking_char": "*", "chars_to_mask": 4, "from_end": False}


def test_when_validate_anonymizer_then_correct_name():
    assert Mask().operator_name() == "mask"
