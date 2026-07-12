import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import EsNifRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return EsNifRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ES_NIF"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # valid NIF scores
        ("55555555K", 1, ((0, 9),),),
        ("55555555-K", 1, ((0, 10),),),
        ("1111111-G", 1, ((0, 9),),),
        ("1111111G", 1, ((0, 8),),),
        ("01111111G", 1, ((0, 9),),),
        # valid NIF in lowercase (control letter is upper-cased before checksum)
        ("55555555k", 1, ((0, 9),),),
        ("12345678z", 1, ((0, 9),),),
        # uppercase still detected
        ("12345678Z", 1, ((0, 9),),),
        # invalid NIF scores
        ("401-023-2138", 0, ()),
        # invalid checksum stays rejected regardless of case
        ("12345678a", 0, ()),
        # fmt: on
    ],
)
def test_when_all_es_nifes_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)
