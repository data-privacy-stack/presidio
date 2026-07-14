import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import DateRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return DateRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["DATE_TIME"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Date tests
        ("Today is 5-20-2021", 1, ((9, 18),), ((0.6, 0.81),),),
        ("Today is 5/20/2021", 1, ((9, 18),), ((0.6, 0.81),),),
        ("Today is 2021-05-21", 1, ((9, 19),), ((0.6, 0.81),),),
        ("Today is 21.5.2021", 1, ((9, 18),), ((0.6, 0.81),),),
        ("Today is 21.5.21", 1, ((9, 16),), ((0.6, 0.81),),),
        ("Today is 5-MAY-2021", 1, ((9, 19),), ((0.6, 0.81),),),
        ("Today is 5-May-2021", 1, ((9, 19),), ((0.6, 0.81),),),
        ("Today is 05/21/21", 1, ((9, 17),), ((0.6, 0.81),),),
        ("Today is 5/21/21", 1, ((9, 16),), ((0.6, 0.81),),),
        ("Today is 21/05/21", 1, ((9, 17),), ((0.6, 0.81),),),
        ("Today is 21/5/21", 1, ((9, 16),), ((0.6, 0.81),),),
        ("Today is May-21", 1, ((9, 15),), ((0.6, 0.81),),),
        ("Today is 21-May", 1, ((9, 15),), ((0.6, 0.81),),),
        ("Today is 05-May", 1, ((9, 15),), ((0.6, 0.81),),),
        ("Today is May-21", 1, ((9, 15),), ((0.6, 0.81),),),
        ("Today is May-2021", 1, ((9, 17),), ((0.6, 0.81),),),
        ("Today is 05/21", 1, ((9, 14),), ((0.05, 0.15),),),
        ("Today is 5/21", 1, ((9, 13),), ((0.05, 0.15),),),
        ("Today is 5/2021", 1, ((9, 15),), ((0.15, 0.25),),),
        ("Today is 05/2021", 1, ((9, 16),), ((0.15, 0.25),),),
        # ISO 8601 tests
        ("Today is 2024-06-05T09:15:30.500-07:00 or not?", 1, ((9, 38),), ((0.6, 0.81),),),
        ("Today is,2024-03-15T14:30:00.123456Z or not?", 1, ((9, 36),), ((0.6, 0.81),),),
        ("Today is\r2024-12-31T23:59:59+00:00 or not?", 1, ((9, 34),), ((0.6, 0.81),),),
        ("Today is\n2024-03-15T14:30:00+02:00 or not?", 1, ((9, 34),), ((0.6, 0.81),),),
        ("Today is 2024-03-15T14:30:00-05:00 or not?", 1, ((9, 34),), ((0.6, 0.81),),),
        ("Today is 2024-03-15T14:30:00.123Z, or not?", 1, ((9, 33),), ((0.6, 0.81),),),
        ("Today is 2024-03-15T14:30:00Z\r or not?", 1, ((9, 29),), ((0.6, 0.81),),),
        ("Today is 2024-03-15T14:30Z\n or not?", 1, ((9, 26),), ((0.6, 0.81),),),
        ("2024-03-15T14:30Z", 1, ((0, 17),), ((0.6, 1),),),
        # Invalid ISO 8601 month/day values must not be detected as a date
        ("2024-13-15T14:30:00Z", 0, (), (),),
        ("2024-00-15T14:30:00Z", 0, (), (),),
        ("2024-12-32T14:30Z", 0, (), (),),
        ("2024-12-00T14:30Z", 0, (), (),),
        ("Today is2024-06-05T09:15:30.500-07:00", 0, (), (),),
        # The leading `\b` must apply to every alternative in the pattern,
        # not just the first one. Without a non-capturing wrapper, the
        # seconds and minutes-only alternatives could match mid-word.
        ("Today is2024-03-15T14:30:00+02:00", 0, (), (),),
        ("Today is2024-03-15T14:30Z", 0, (), (),),
        # Word boundary tests
        ("Today is5/21", 0, (), (),),
        ("Today is5/21and it's sunny", 0, (), (),),
        ("Today is,5/21,and it's sunny", 1, ((9, 13),), ((0.05, 0.15),),),
        ("5-20-2021 is today.", 1, ((0, 9),), ((0.6, 0.81),),),
        ("5-20-2021", 1, ((0, 9),), ((0.6, 0.81),),),        
        # fmt: on
    ],
)
def test_when_all_dates_then_succeed(
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
