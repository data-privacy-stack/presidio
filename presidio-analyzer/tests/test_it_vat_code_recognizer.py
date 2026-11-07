import pytest

from presidio_analyzer.predefined_recognizers import ItVatCodeRecognizer
from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return ItVatCodeRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IT_VAT_CODE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Test with an invalid VAT Code
        ("00000000000", 0, (), ()),
        # Test with an invalid VAT Code
        ("00000000001", 0, (), ()),
        # Test with a valid VAT Code
        ("01333550323", 1, ((0, 11),), ((0.9, 1.0),),),
        # Test with two codes but only the second is a valid VAT code
        ("00000000000 and 01333550323", 1, ((16, 27),), ((0.9, 1.0),)),
        # Test with a valid VAT Code and a character that needs to be replaced
        ("01333550_323", 1, ((0, 12),), ((0.9, 1.0),),),
        # Test that a trailing space is not part of the result span
        ("01333550323 is valid", 1, ((0, 11),), ((0.9, 1.0),),),
        ("piva 01333550323 di Mario", 1, ((5, 16),), ((0.9, 1.0),),),
        # Test that a trailing underscore is not part of the result span
        ("01333550323_ ok", 1, ((0, 11),), ((0.9, 1.0),),),
        # Test with spaces inside the code and a trailing space
        ("013 335 503 23 ok", 1, ((0, 14),), ((0.9, 1.0),),),
        # Test that a 12-digit number is not detected
        ("013335503231", 0, (), ()),
        # fmt: on
    ],
)
def test_when_fiscalcode_in_text_then_all_it_fiscalcode_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )
