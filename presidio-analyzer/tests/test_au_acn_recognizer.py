import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import AuAcnRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return AuAcnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["AU_ACN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid formatting and valid ACNs
        ("000 000 019", 1, ((0, 11),), ((1.0, 1.0),), ),
        ("005 499 981", 1, ((0, 11),), ((1.0, 1.0),), ),
        ("006249976", 1, ((0, 9),), ((1.0, 1.0),), ),
        # Valid ACN whose check digit is 0 (weighted sum is a multiple of 10)
        ("000000180", 1, ((0, 9),), ((1.0, 1.0),), ),
        # Valid formatting but invalid ACNs 
        ("824 753 557", 0, (), (),),
        ("824753557", 0, (), (),),
        # Invalid formatting and ACNs.
        ("5282475355632", 0, (), (),),
        ("52824753556AF", 0, (), (),),
        ("51 824 753 5564", 0, (), (),),
        ("123 456\n789", 0, (), (),),
    ],
)
def test_when_all_acns_then_succeed(
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
