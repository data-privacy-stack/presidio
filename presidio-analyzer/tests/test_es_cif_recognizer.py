from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import EsCifRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result

PATTERN_SCORE = 0.4


@pytest.fixture(scope="module")
def recognizer():
    return EsCifRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ES_CIF"]


@pytest.mark.parametrize(
    "text, expected_positions",
    [
        # fmt: off
        # A and B keys take a control digit
        ("B12345674", ((0, 9),)),
        ("A13585625", ((0, 9),)),
        # P, Q, R, S, N and W keys take a control letter
        ("P1234567D", ((0, 9),)),
        ("Q2345678C", ((0, 9),)),
        # other keys take either
        ("J99216582", ((0, 9),)),
        ("J9921658B", ((0, 9),)),
        # non-resident A to H entities (digits starting 00) may use the letter
        ("A0012345E", ((0, 9),)),
        # hyphens and lowercase
        ("B-12345674", ((0, 10),)),
        ("B-1234567-4", ((0, 11),)),
        ("b12345674", ((0, 9),)),
        ("La sociedad B-12345674, con domicilio en Madrid", ((12, 22),)),
        # fmt: on
    ],
)
def test_when_valid_cif_then_detected_at_pattern_score(
    text, expected_positions, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert len(results) == len(expected_positions)
    for result, (start, end) in zip(results, expected_positions):
        assert_result(result, entities[0], start, end, PATTERN_SCORE)


@pytest.mark.parametrize(
    "text",
    [
        # fmt: off
        "B12345675",    # wrong control digit
        "B1234567D",    # right value, but B keys take a digit
        "P12345674",    # right value, but P keys take a letter
        "A12345678",    # product-code lookalike with a wrong control digit
        "I12345674",    # I is not an entity key
        "X1234567L",    # an NIE, not an entity
        "B123456744",   # too long
        # fmt: on
    ],
)
def test_when_invalid_cif_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


def test_when_context_word_precedes_cif_then_score_increases(spacy_nlp_engine):
    """The control character does not prove a CIF, so context raises the score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(EsCifRecognizer(supported_language="en"))
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)

    with_context = analyzer.analyze("Company CIF B12345674", language="en")
    without_context = analyzer.analyze("Reference B12345674", language="en")
    # context is prefix-only by default, so a following word does not count
    context_after = analyzer.analyze("B12345674 is the CIF", language="en")

    assert [r.score for r in without_context] == [pytest.approx(PATTERN_SCORE)]
    assert [r.score for r in with_context] == [pytest.approx(0.75)]
    assert [r.score for r in context_after] == [pytest.approx(PATTERN_SCORE)]


def test_cif_loads_and_detects_when_enabled_in_yaml(entities):
    """The shipped YAML entry builds a working recognizer once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == "EsCifRecognizer")
    assert entry["enabled"] is False
    assert entry["country_code"] == "es"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["es"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["EsCifRecognizer"]
    results = registry.recognizers[0].analyze("CIF: B-12345674", entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 5, 15, PATTERN_SCORE)
