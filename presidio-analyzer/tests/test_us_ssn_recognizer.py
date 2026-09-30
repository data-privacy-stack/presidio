import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import UsSsnRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return UsSsnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["US_SSN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # very weak match
        ("078-051121 07805-1121", 2, ((0, 10), (11, 21),), ((0.0, 0.3), (0.0, 0.3),),),
        # weak match
        ("078051121", 1, ((0, 9),), ((0.0, 0.4),),),
        # medium match
        ("078-05-1123", 1, ((0, 11),), ((0.5, 0.6),),),
        ("078.05.1123", 1, ((0, 11),), ((0.5, 0.6),),),
        ("078 05 1123", 1, ((0, 11),), ((0.5, 0.6),),),
        ("abc 078 05 1123 abc", 1, ((4, 15),), ((0.5, 0.6),),),
        # The canonical "123-45-6789" sample literal must not prefix-block the
        # neighbouring 123-45-678X family; only the canonical sample is
        # invalidated (by exact match), the rest are valid SSN-shaped values
        ("123-45-6781", 1, ((0, 11),), ((0.5, 0.6),),),
        ("123-45-6782", 1, ((0, 11),), ((0.5, 0.6),),),
        ("123-45-6783", 1, ((0, 11),), ((0.5, 0.6),),),
        ("123-45-6784", 1, ((0, 11),), ((0.5, 0.6),),),
        ("123-45-6785", 1, ((0, 11),), ((0.5, 0.6),),),
        ("123-45-6786", 1, ((0, 11),), ((0.5, 0.6),),),
        ("123-45-6787", 1, ((0, 11),), ((0.5, 0.6),),),
        ("123-45-6788", 1, ((0, 11),), ((0.5, 0.6),),),
        # a normal valid SSN is still detected
        ("219-09-9999", 1, ((0, 11),), ((0.5, 0.6),),),
        # no match
        ("0780511201", 0, (), (),),
        ("078051120", 0, (), (),),
        ("000000000", 0, (), (),),
        ("666000000", 0, (), (),),
        ("078-05-0000", 0, (), (),),
        ("078 00 1123", 0, (), (),),
        ("693-09.4444", 0, (), (),),
        # canonical sample SSNs stay invalidated (now via exact match)
        ("987-65-4320", 0, (), (),),
        ("078-05-1120", 0, (), (),),
        ("123-45-6789", 0, (), (),),
        # never-issued area numbers (000/666 and the 900 series) stay
        # invalidated via the area check
        ("000-12-3456", 0, (), (),),
        ("666-12-3456", 0, (), (),),
        ("900-12-3456", 0, (), (),),
        ("999-12-3456", 0, (), (),),
        ("900123456", 0, (), (),),
        # 899 is the highest valid area number and stays detected
        ("899-12-3456", 1, ((0, 11),), ((0.5, 0.6),),),
        # fmt: on
    ],
)
def test_when_snn_in_text_than_all_us_ssns_are_found(
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


def test_recognizer_loads_and_detects_when_enabled_in_yaml():
    """Detection must work through the path users actually configure."""
    from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "UsSsnRecognizer",
                    "supported_languages": ["en"],
                    "type": "predefined",
                    "enabled": True,
                    "country_code": "us",
                }
            ],
        }
    ).create_recognizer_registry()

    recognizer = registry.get_recognizers(language="en", entities=["US_SSN"])
    assert len(recognizer) == 1

    results = recognizer[0].analyze("ssn 219-09-9999", entities=["US_SSN"])
    assert len(results) == 1
    assert results[0].entity_type == "US_SSN"
    assert (results[0].start, results[0].end) == (4, 15)

    # 900-series area numbers are rejected through the configured path too
    assert recognizer[0].analyze("ssn 900-12-3456", entities=["US_SSN"]) == []
