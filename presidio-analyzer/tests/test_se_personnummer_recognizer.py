from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import EntityRecognizer
from presidio_analyzer.predefined_recognizers import SePersonnummerRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


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


def test_date_check_applies_when_enabled_in_default_yaml():
    """The recognizer users enable in YAML rejects impossible dates too.

    The shipped entry supports only ``sv``, so the top-level
    ``supported_languages`` must include ``sv`` or nothing loads.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "SePersonnummerRecognizer"]
    assert len(entries) == 1

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["sv"],
            "recognizers": [dict(entries[0], enabled=True)],
        }
    ).create_recognizer_registry()
    [loaded] = registry.recognizers

    valid = loaded.analyze("Personnummer 880229-2386.", ["SE_PERSONNUMMER"])
    assert [(r.start, r.end) for r in valid] == [(13, 24)]
    assert valid[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)
    assert loaded.analyze("Personnummer 870231-2383.", ["SE_PERSONNUMMER"]) == []
