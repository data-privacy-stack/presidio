import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import AuBankDetailsRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return AuBankDetailsRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["AU_BANK_DETAILS"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid BSB + account formats.
        ("062-000 12345678", 1, ((0, 16),), ((1.0, 1.0),),),
        ("062 000 123456", 1, ((0, 14),), ((1.0, 1.0),),),
        ("BSB: 062-000 Account: 12345678", 1, ((0, 30),), ((1.0, 1.0),),),
        # Invalid account length.
        ("062-000 12345", 0, (), (),),
        # Invalid structural values.
        ("000-000 12345678", 0, (), (),),
        ("062-000 000000", 0, (), (),),
        # Invalid formats.
        ("06200012345678", 0, (), (),),
        ("123 456\n789012", 0, (), (),),
    ],
)
def test_when_all_au_bank_details_then_succeed(
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