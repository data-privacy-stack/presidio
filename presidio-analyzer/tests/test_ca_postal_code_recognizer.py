import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import CaPostalCodeRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return CaPostalCodeRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CA_POSTAL_CODE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # --- Valid, canonical spaced form (medium) ---
        ("K1A 0B1", 1, ((0, 7),), ((0.4, 0.81),),),
        ("M5V 2T6", 1, ((0, 7),), ((0.4, 0.81),),),
        ("H0H 0H0", 1, ((0, 7),), ((0.4, 0.81),),),
        # W and Z are permitted in non-leading letter positions
        ("N1W 2Z9", 1, ((0, 7),), ((0.4, 0.81),),),
        # Case-insensitive (re.IGNORECASE)
        ("k1a 0b1", 1, ((0, 7),), ((0.4, 0.81),),),

        # --- Valid, space omitted (weak) ---
        ("K1A0B1", 1, ((0, 6),), ((0.0, 0.3),),),
        ("M5V2T6", 1, ((0, 6),), ((0.0, 0.3),),),

        # --- Valid within surrounding context (English / French) ---
        ("My postal code is K1A 0B1", 1, ((18, 25),), ((0.4, 0.81),),),
        ("Mon code postal est H2X 1Y4", 1, ((20, 27),), ((0.4, 0.81),),),

        # --- Invalid: letters excluded as the first letter (D, W, Z) ---
        ("D1A 0B1", 0, (), (),),
        ("W1A 0B1", 0, (), (),),
        ("Z1A 0B1", 0, (), (),),

        # --- Invalid: letters never used anywhere (D, F, I, O, Q, U) ---
        ("K1D 0B1", 0, (), (),),
        ("K1A 0O1", 0, (), (),),

        # --- Invalid: wrong length ---
        ("K1A 0B", 0, (), (),),
        ("K1A 0B12", 0, (), (),),

        # --- Invalid: digit where a letter is required ---
        ("11A 0B1", 0, (), (),),

        # --- Invalid: unsupported separators ---
        ("K1A-0B1", 0, (), (),),
        ("K1A  0B1", 0, (), (),),
        # fmt: on
    ],
)
def test_when_postal_code_in_text_then_all_ca_postal_codes_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )
