import pytest

from tests import (
    BENGALI_DIGITS,
    DEVANAGARI_DIGITS,
    ODIA_DIGITS,
    assert_result,
)
from presidio_analyzer.predefined_recognizers import InPanRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return InPanRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_PAN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        ("AAASA1111R", 1, (0,10), 0.1) ,
        ("ABCPD1234Z", 1, (0, 10), 0.5),
        ("ABCND1234Z", 1, (0, 10), 0.1),
        ("A1111DFSFS", 1, (0,10),0.01),
        ("ABCD1234",0,(),(),),
        ("My PAN number is ABBPM4567S with a lot of text beyond it", 1, (17,27),.5),
        # fmt: on
    ],
)
def test_when_pan_in_text_then_all_pans_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
):
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


@pytest.mark.parametrize(
    "table",
    [DEVANAGARI_DIGITS, BENGALI_DIGITS, ODIA_DIGITS],
    ids=["devanagari", "bengali", "odia"],
)
def test_when_pan_indic_digits_then_same_span_and_score_as_ascii(
    recognizer,
    entities,
    table,
):
    ascii_text = "My PAN number is ABBPM4567S."

    expected = recognizer.analyze(ascii_text, entities)
    actual = recognizer.analyze(ascii_text.translate(table), entities)

    assert [(r.start, r.end, r.score) for r in expected] == [(17, 27, 0.5)]
    assert [(r.start, r.end, r.score) for r in actual] == [
        (r.start, r.end, r.score) for r in expected
    ]
