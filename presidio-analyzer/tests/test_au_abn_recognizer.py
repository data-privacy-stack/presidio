import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import AuAbnRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return AuAbnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["AU_ABN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid formatting and valid ABNs 
        ("51 824 753 556", 1, ((0, 14),), ((1.0, 1.0),), ),
        ("51824753556", 1, ((0, 11),), ((1.0, 1.0),), ),
        # Valid formatting but invalid ABNs
        ("52 824 753 556", 0, (), (),),
        ("52824753556", 0, (), (),),
        # Leading-zero number: a valid ABN never starts with 0, and the ABR
        # algorithm's literal "subtract 1 from the first digit" makes it fail.
        # (A prior special case remapped the leading 0 to 9 and wrongly
        # accepted this as valid.)
        ("00000000560", 0, (), (),),
        # Invalid formatting and ABNs.  
        ("5282475355632", 0, (), (),),
        ("52824753556AF", 0, (), (),),
        ("51 824 753 5564", 0, (), (),),
        ("123 456\n789", 0, (), (),),
    ],
)
def test_when_all_abns_then_succeed(
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
