import pytest
from presidio_analyzer.predefined_recognizers import NgNinRecognizer

from tests.assertions import assert_result_within_score_range


def _generate_verhoeff_digit(num_str: str) -> str:
    """Generate a Verhoeff check digit for a numeric string."""
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
    digits = list(map(int, reversed(num_str)))
    for i in range(len(digits)):
        c = __d__[c][__p__[(i + 1) % 8][digits[i]]]
    return str(__inv__[c])


# Pre-generated valid 11-digit NINs (10 random digits + Verhoeff check digit)
VALID_NIN_1 = "1234567890" + _generate_verhoeff_digit("1234567890")
VALID_NIN_2 = "9876543210" + _generate_verhoeff_digit("9876543210")
VALID_NIN_3 = "5551234567" + _generate_verhoeff_digit("5551234567")
# A valid 11-digit NIN whose first digit is 0 (no rule forbids it).
VALID_NIN_LEADING_ZERO = "0123456789" + _generate_verhoeff_digit("0123456789")


@pytest.fixture(scope="module")
def recognizer():
    return NgNinRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["NG_NIN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid NINs (validate_result promotes score to 1.0)
        (
            VALID_NIN_1,
            1,
            ((0, 11),),
            ((1.0, 1.0),),
        ),
        (
            f"NIN: {VALID_NIN_2}",
            1,
            ((5, 16),),
            ((1.0, 1.0),),
        ),
        (
            f"My NIN is {VALID_NIN_1} and yours is {VALID_NIN_3}",
            2,
            ((10, 21), (35, 46)),
            ((1.0, 1.0), (1.0, 1.0)),
        ),
        # Valid NIN whose first digit is 0 — must still validate (the checksum
        # was previously computed on int(value), dropping the leading zero).
        (
            VALID_NIN_LEADING_ZERO,
            1,
            ((0, 11),),
            ((1.0, 1.0),),
        ),
        # Invalid: fails Verhoeff checksum (flip last digit)
        (
            "12345678901",
            0,
            (),
            (),
        ),
        # Invalid: wrong length (10 digits)
        (
            "1234567890",
            0,
            (),
            (),
        ),
        # Invalid: wrong length (12 digits)
        (
            "123456789012",
            0,
            (),
            (),
        ),
        # Invalid: embedded in longer number (not word boundary)
        (
            f"99{VALID_NIN_1}88",
            0,
            (),
            (),
        ),
        # Invalid: non-numeric
        (
            "1234567890a",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_nin_in_text_then_all_ng_nins_found(
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


class TestVerhoeffChecksum:
    """Direct tests for the Verhoeff checksum method."""

    def test_when_valid_verhoeff_then_returns_true(self):
        assert NgNinRecognizer._is_verhoeff_number(VALID_NIN_1) is True

    def test_when_invalid_verhoeff_then_returns_false(self):
        # Flip the last digit to break the checksum
        broken = VALID_NIN_1[:-1] + str((int(VALID_NIN_1[-1]) + 1) % 10)
        assert NgNinRecognizer._is_verhoeff_number(broken) is False

    def test_when_eleven_zeros_then_returns_false(self):
        # 11 zeros is not a valid Verhoeff number. (The previous version passed
        # int(0), which the helper stringified to a single "0" — itself valid —
        # so it never exercised the 11-digit all-zero case.)
        assert NgNinRecognizer._is_verhoeff_number("00000000000") is False

    def test_when_single_zero_then_returns_true(self):
        assert NgNinRecognizer._is_verhoeff_number("0") is True

    def test_when_leading_zero_then_not_dropped(self):
        # Regression: the checksum used to run on int(value), dropping a
        # leading zero and shortening the digit string, so a valid 11-digit
        # NIN beginning with 0 was wrongly rejected.
        assert NgNinRecognizer._is_verhoeff_number(VALID_NIN_LEADING_ZERO) is True
        assert VALID_NIN_LEADING_ZERO[0] == "0"
