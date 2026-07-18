import pytest

from presidio_analyzer.predefined_recognizers import NgBvnRecognizer
from tests.assertions import assert_result_within_score_range

# Representative 11-digit BVN values used throughout the tests.
# These are synthetic — they follow the 11-digit format but are not real BVNs.
VALID_BVN_1 = "22345678901"
VALID_BVN_2 = "98765432101"
VALID_BVN_3 = "55512345678"


@pytest.fixture(scope="module")
def recognizer():
    return NgBvnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["NG_BVN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off

        # --- Without context: score stays at pattern base (very low) ---

        # Bare BVN, no context — very weak signal
        (
            VALID_BVN_1,
            1,
            ((0, 11),),
            ((0.0, 0.29),),
        ),
        # Two bare BVNs, no context
        (
            f"{VALID_BVN_1} and {VALID_BVN_2}",
            2,
            ((0, 11), (16, 27)),
            ((0.0, 0.29), (0.0, 0.29)),
        ),

        # --- With context: score is boosted above the low base ---

        # Exact context word "bvn"
        (
            f"bvn: {VALID_BVN_1}",
            1,
            ((5, 16),),
            ((0.3, 1.0),),
        ),
        # Full context phrase
        (
            f"bank verification number: {VALID_BVN_2}",
            1,
            ((26, 37),),
            ((0.3, 1.0),),
        ),
        # Context word in sentence, BVN separated by whitespace
        (
            f"Please provide your BVN for KYC. Your BVN is {VALID_BVN_3}.",
            1,
            ((46, 57),),
            ((0.3, 1.0),),
        ),
        # NIBSS context word
        (
            f"NIBSS BVN record: {VALID_BVN_1}",
            1,
            ((18, 29),),
            ((0.3, 1.0),),
        ),

        # --- Invalid inputs: must not be detected ---

        # Wrong length: 10 digits
        (
            "2234567890",
            0,
            (),
            (),
        ),
        # Wrong length: 12 digits
        (
            "223456789012",
            0,
            (),
            (),
        ),
        # Non-numeric characters
        (
            "2234567890a",
            0,
            (),
            (),
        ),
        # Embedded in a longer number: word boundary must not match
        (
            f"99{VALID_BVN_1}88",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_bvn_in_text_then_expected_results(
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


class TestBvnValidation:
    """Unit tests for NgBvnRecognizer.validate_result."""

    def test_valid_11_digit_bvn_returns_none(self):
        recognizer = NgBvnRecognizer()
        # Returns None (not True) to preserve context-driven score.
        assert recognizer.validate_result(VALID_BVN_1) is None

    def test_10_digit_string_returns_false(self):
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("2234567890") is False

    def test_12_digit_string_returns_false(self):
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("223456789012") is False

    def test_non_numeric_returns_false(self):
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("2234567890a") is False

    def test_all_zeros_11_digits_returns_none(self):
        # All-zeros is numerically valid format (11 digits, all numeric).
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("00000000000") is None
