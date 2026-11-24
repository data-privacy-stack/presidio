import pytest

from tests import ARABIC_INDIC_DIGITS, PERSIAN_DIGITS, assert_result
from presidio_analyzer.predefined_recognizers import CreditCardRecognizer

# https://www.datatrans.ch/showcase/test-cc-numbers
# https://www.freeformatter.com/credit-card-number-generator-validator.html


@pytest.fixture(scope="module")
def cc_recognizer():
    return CreditCardRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CREDIT_CARD"]


@pytest.mark.parametrize(
    "text, expected_len, expected_scores, expected_res",
    [
        # fmt: off
        (
            "4012888888881881 4012-8888-8888-1881 4012 8888 8888 1881",
            3, (), ((0, 16), (17, 36), (37, 56),),
        ),
        ("1748503543012", 0, (), (),),
        ("122000000000003", 1, (), ((0, 15),),),
        ("my credit card: 122000000000003", 1, (), ((16, 31),),),
        ("371449635398431", 1, (), ((0, 15),),),
        ("5555555555554444", 1, (), ((0, 16),),),
        ("5019717010103742", 1, (), ((0, 16),),),
        ("30569309025904", 1, (), ((0, 14),),),
        ("6011000400000000", 1, (), ((0, 16),),),
        ("3528000700000000", 1, (), ((0, 16),),),
        ("6759649826438453", 1, (), ((0, 16),),),
        ("5555555555554444", 1, (), ((0, 16),),),
        ("4111111111111111", 1, (), ((0, 16),),),
        ("4917300800000000", 1, (), ((0, 16),),),
        ("4484070000000000", 1, (1.0,), ((0, 16),),),
        ("4012-8888-8888-1882", 0, (), (),),
        ("my credit card number is 4012-8888-8888-1882", 0, (), (),),
        ("36168002586008", 0, (), (),),
        ("my credit card number is 36168002586008", 0, (), (),),
        # fmt: on
    ],
)
def test_when_all_credit_cards_then_succeed(
    text,
    expected_len,
    expected_scores,
    expected_res,
    cc_recognizer,
    entities,
    max_score,
):
    results = cc_recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, expected_score in zip(results, expected_scores):
        assert res.score == expected_score
    for res, (start, end) in zip(results, expected_res):
        assert_result(res, entities[0], start, end, max_score)


@pytest.mark.parametrize(
    "table", [ARABIC_INDIC_DIGITS, PERSIAN_DIGITS], ids=["arabic-indic", "persian"]
)
def test_when_card_number_non_ascii_digits_then_same_span_as_ascii(
    cc_recognizer, entities, table
):
    ascii_text = "My card is 4012888888881881 thanks"

    expected = cc_recognizer.analyze(ascii_text, entities)
    actual = cc_recognizer.analyze(ascii_text.translate(table), entities)

    assert [(r.start, r.end) for r in expected] == [(11, 27)]
    assert [(r.start, r.end, r.score) for r in actual] == [
        (r.start, r.end, r.score) for r in expected
    ]
