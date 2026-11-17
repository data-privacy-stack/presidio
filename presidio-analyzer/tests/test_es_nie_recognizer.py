import pytest
from pathlib import Path

import presidio_analyzer
import yaml
from presidio_analyzer import Pattern
from presidio_analyzer.predefined_recognizers import EsNieRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the EsNieRecognizer."""
    return EsNieRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return entities to analyze."""
    return ["ES_NIE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # valid NIE scores
        ("Z8078221M", 1, ((0, 9),),),
        ("X9613851N", 1, ((0, 9),),),
        ("Y8063915Z", 1, ((0, 9),),),
        ("Y8063915-Z", 1, ((0, 10),),),
        ("Mi NIE es X9613851N", 1, ((10, 19),),),
        ("Z8078221M en mi NIE", 1, ((0, 9),),),
        ("Mi Número de identificación de extranjero es Y8063915-Z", 1, \
            ((45, 55),),),
        # valid NIE in lowercase (prefix and control letter are upper-cased
        # before checksum)
        ("x9613851n", 1, ((0, 9),),),
        ("z8078221m", 1, ((0, 9),),),
        # uppercase still detected
        ("X9613851N", 1, ((0, 9),),),
        # invalid NIE scores
        ("Y8063915Q", 0, ()),
        ("Y806391Q", 0, ()),
        ("58063915Q", 0, ()),
        ("W8063915Q", 0, ()),
        # invalid checksum stays rejected regardless of case
        ("x9613851q", 0, ()),
        # a hyphen after the prefix letter, or a space after an uppercase one;
        # the whole value, prefix included, is the entity
        ("X-1234567-L", 1, ((0, 11),),),
        ("X-1234567L", 1, ((0, 10),),),
        ("x-1234567-l", 1, ((0, 11),),),
        ("Y 1234567X", 1, ((0, 10),),),
        ("Z-1234567-R", 1, ((0, 11),),),
        ("Mi NIE es X-1234567-L.", 1, ((10, 21),),),
        # separators do not bypass the checksum
        ("X-1234567-M", 0, ()),
        # a lowercase letter and a space is a word, not a prefix
        ("x 1234567L", 0, ()),
        # no space before the control letter
        ("X 1234567 L", 0, ()),
    ],
)
def test_when_all_es_nie_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    """Tests the ES_NIE recognizer against valid & invalid examples."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


def test_when_custom_pattern_allows_non_digit_middle_then_no_crash(entities):
    """A non-digit middle segment should be rejected, not raise."""
    loose_pattern = Pattern("NIE_LOOSE", r"\b[X-Z][0-9A-Za-z]{6}[A-Z]\b", 0.5)
    recognizer = EsNieRecognizer(patterns=[loose_pattern])
    results = recognizer.analyze("XABCDEFG", entities)
    assert results == []


def test_nie_loads_and_detects_when_enabled_in_yaml(entities, max_score):
    """The shipped YAML entry builds a recognizer that detects separated NIEs."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == "EsNieRecognizer")

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["es"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["EsNieRecognizer"]
    results = registry.recognizers[0].analyze("NIE X-1234567-L", entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 4, 15, max_score)
