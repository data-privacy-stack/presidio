import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import SePersonnummerRecognizer


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the SePersonnummerRecognizer."""
    return SePersonnummerRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return entities to analyze."""
    return ["SE_PERSONNUMMER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # Valid Swedish personnummer.
        (
            "189004119807",
            1,
            ((0, 12),),
        ),
        (
            "My personal identity code is: 189110089811. Thank you.",
            1,
            ((30, 42),),
        ),
        (
            "191005059801",
            1,
            ((0, 12),),
        ),
        (
            "198712202384",
            1,
            ((0, 12),),
        ),
        (
            "871220-2384",
            1,
            ((0, 11),),
        ),
        (
            "199109242397 är mitt pnr.",
            1,
            ((0, 12),),
        ),
        (
            "19910924-2397 är mitt pnr.",
            1,
            ((0, 13),),
        ),
        (
            "199201232387",
            1,
            ((0, 12),),
        ),
        (
            "9201232387",
            1,
            ((0, 10),),
        ),
        (
            "Here's my personnummer 200109022392.",
            1,
            ((23, 35),),
        ),
        (
            "201109252385",
            1,
            ((0, 12),),
        ),
        (
            "20110925-2385",
            1,
            ((0, 13),),
        ),
        (
            "My swedish id code is199003052397.",
            1,
            ((21, 33),),
        ),
        # invalid Personal Identity Codes scores
        ("19000309-3393", 0, ()),
        ("19001309-2393", 0, ()),
        ("200504422381", 0, ()),
        ("189x09179809", 0, ()),
        ("18970c17-9809", 0, ()),
        # Days that do not exist in their month, with valid check digits.
        ("870231-2383", 0, ()),  # 31 February
        ("870431-2381", 0, ()),  # 31 April
        ("870229-2387", 0, ()),  # 29 February in a non-leap year
        ("19870229-2387", 0, ()),
        ("870291-2380", 0, ()),  # samordningsnummer for 31 February
        ("880229-2386", 1, ((0, 11),)),  # 29 February 1988
        ("19880229-2386", 1, ((0, 13),)),
    ],
)
def test_when_all_swedish_personnummer_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    """Tests our recognizer against valid & invalid Swedish personnummer."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)
