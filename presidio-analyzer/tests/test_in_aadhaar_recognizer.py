import pytest

from tests import (
    BENGALI_DIGITS,
    DEVANAGARI_DIGITS,
    ODIA_DIGITS,
    assert_result,
)
from presidio_analyzer.predefined_recognizers import InAadhaarRecognizer


@pytest.fixture(scope="module")
def recognizer() -> InAadhaarRecognizer:
    return InAadhaarRecognizer()


@pytest.fixture(scope="module")
def entities() -> list[str]:
    return ["IN_AADHAAR"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        ("123456789012", 0, (0,12), 0),
        ("312345678909", 1, (0, 12), 1),
        ("399876543211", 1, (0, 12), 1),
        ("1234 5678 9012", 0, (0,14), 0),
        ("3123 4567 8909", 1, (0, 14), 1),
        ("3998 7654 3211", 1, (0, 14), 1),
        ("1234-5678-9012", 0, (0,14), 0),
        ("3123-4567-8909", 1, (0, 14), 1),
        ("3998-7654-3211", 1, (0, 14), 1),
        ("1234:5678:9012", 0, (0,14), 0),
        ("3123:4567:8909", 1, (0, 14), 1),
        ("3998:7654:3211", 1, (0, 14), 1),
        ("My Aadhaar number is 400123456787 with a lot of text beyond it", 1, (21,33), 1),
        # fmt: on
    ],
)
def test_when_aadhaar_in_text_then_all_aadhaars_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
) -> None:
    results = recognizer.analyze(text, entities)
    print(results)

    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )

palindrome_test_set = [
    ["abMA", False, False],
    ["abCba", False, True],
    ["ABBA", False, True],
    ["aBba", True, True],
    ["NotAPalindrome", True, False],
]


@pytest.mark.parametrize(
    "input_text,case_sensitive, expected_output", palindrome_test_set
)
def test_is_palindrome(input_text, case_sensitive, expected_output):
    """
    Test if input is a true palindrome as defined in base class.

    :param input_text: input text to validate
    :param case_sensitive: flag to calculate palindrome with no case
    :param expected_output: calculated output
    :return: True/False
    """
    assert (
            InAadhaarRecognizer._is_palindrome(input_text, case_sensitive)
            == expected_output
    )


verhoeff_test_set = [
    [312345678909, True],
    [400123456787, True],
    [123456789012, False],
]

@pytest.mark.parametrize("input_number, is_verhoeff", verhoeff_test_set)
def test_is_verhoeff(input_number, is_verhoeff) -> None:
    """
    Test to assert verhoeff number validation based on checksum from base class.

    :param input_number: input integer
    :param is_verhoeff: expected flag
    :return: True/False
    """
    assert InAadhaarRecognizer._is_verhoeff_number(input_number) == is_verhoeff


@pytest.mark.parametrize(
    "table",
    [DEVANAGARI_DIGITS, BENGALI_DIGITS, ODIA_DIGITS],
    ids=["devanagari", "bengali", "odia"],
)
def test_when_aadhaar_indic_digits_then_matches_valid_and_rejects_invalid(
    recognizer: InAadhaarRecognizer,
    entities: list[str],
    table: dict[int, int],
) -> None:
    valid_ascii = "My Aadhaar is 3123 4567 8909."
    invalid_ascii = "My Aadhaar is 1234 5678 9012."

    expected = recognizer.analyze(valid_ascii, entities)
    actual = recognizer.analyze(valid_ascii.translate(table), entities)

    assert [(r.start, r.end, r.score) for r in expected] == [(14, 28, 1.0)]
    assert [(r.start, r.end, r.score) for r in actual] == [
        (r.start, r.end, r.score) for r in expected
    ]
    assert recognizer.analyze(invalid_ascii.translate(table), entities) == []
