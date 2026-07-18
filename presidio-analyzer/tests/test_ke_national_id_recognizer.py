import pytest

from presidio_analyzer.predefined_recognizers import KeNationalIdRecognizer
from tests.assertions import assert_result_within_score_range

# Synthetic Kenyan national ID numbers used throughout the tests.
VALID_ID_8 = "12345678"   # 8-digit (current format)
VALID_ID_7 = "1234567"    # 7-digit (older cards)


@pytest.fixture(scope="module")
def recognizer():
    return KeNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["KE_NATIONAL_ID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off

        # --- Without context: score stays at pattern base (very low) ---

        (
            VALID_ID_8,
            1,
            ((0, 8),),
            ((0.0, 0.29),),
        ),
        (
            VALID_ID_7,
            1,
            ((0, 7),),
            ((0.0, 0.29),),
        ),

        # --- With context: score is boosted ---

        (
            f"national id: {VALID_ID_8}",
            1,
            ((13, 21),),
            ((0.3, 1.0),),
        ),
        (
            f"Kenya national id number: {VALID_ID_7}",
            1,
            ((26, 33),),
            ((0.3, 1.0),),
        ),
        (
            f"nid: {VALID_ID_8}",
            1,
            ((5, 13),),
            ((0.3, 1.0),),
        ),
        (
            f"national identity card: {VALID_ID_8}",
            1,
            ((23, 31),),
            ((0.3, 1.0),),
        ),
        (
            f"Kenyan id {VALID_ID_7} was reported",
            1,
            ((10, 17),),
            ((0.3, 1.0),),
        ),

        # --- Invalid inputs ---

        # 6 digits: below minimum length
        (
            "123456",
            0,
            (),
            (),
        ),
        # 9 digits: above maximum length
        (
            "123456789",
            0,
            (),
            (),
        ),
        # Non-numeric
        (
            "1234567a",
            0,
            (),
            (),
        ),
        # Embedded in a longer number (word boundary)
        (
            f"99{VALID_ID_8}88",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_ke_national_id_in_text_then_expected_results(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


class TestKeNationalIdValidation:
    """Unit tests for KeNationalIdRecognizer.validate_result."""

    def test_8_digit_id_returns_none(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result(VALID_ID_8) is None

    def test_7_digit_id_returns_none(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result(VALID_ID_7) is None

    def test_6_digit_returns_false(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result("123456") is False

    def test_9_digit_returns_false(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result("123456789") is False

    def test_non_numeric_returns_false(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result("1234567a") is False
