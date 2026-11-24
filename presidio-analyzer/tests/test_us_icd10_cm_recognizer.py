"""Tests for the US ICD-10-CM recognizer."""

from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import UsIcd10CmRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

ENTITY = "US_ICD10_CM"


@pytest.fixture(scope="module")
def recognizer():
    """Direct recognizer instance."""
    return UsIcd10CmRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Entities requested from the recognizer."""
    return [ENTITY]


@pytest.mark.parametrize(
    "text, match",
    [
        ("E11.9", "E11.9"),
        ("J45.909", "J45.909"),
        ("S72.001A", "S72.001A"),
        ("T36.0X1A", "T36.0X1A"),
        ("Z79.4", "Z79.4"),
        ("M54.5", "M54.5"),
        ("C4A.0", "C4A.0"),
        ("C7A.010", "C7A.010"),
        ("C7B.00", "C7B.00"),
        ("D3A.00", "D3A.00"),
        ("O9A.119", "O9A.119"),
        ("M1A.00X0", "M1A.00X0"),
        ("Z3A.08", "Z3A.08"),
        ("Patient coded as (E11.9).", "E11.9"),
        ("Ended with M54.5.", "M54.5"),
    ],
)
def test_when_dotted_code_then_detected_with_exact_score_and_bounds(
    text, match, recognizer, entities
):
    """A dotted code is found at the weak score with exact boundaries."""
    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    start = text.index(match)
    assert results[0].entity_type == ENTITY
    assert (results[0].start, results[0].end) == (start, start + len(match))
    assert results[0].score == pytest.approx(0.1)


def test_when_two_codes_then_both_detected(recognizer, entities):
    """Several codes in one text are all returned."""
    text = "Codes E11.9, J45.909 and Z79.4"

    results = recognizer.analyze(text, entities)

    assert [text[r.start : r.end] for r in results] == ["E11.9", "J45.909", "Z79.4"]


@pytest.mark.parametrize(
    "text",
    [
        "E11",  # three-character category: known gap
        "E119",  # undotted code: known gap
        "A1.2",  # first digit group too short
        "E11.",  # no characters after the decimal point
        "E11.12345",  # five characters after the decimal point
        "192.168.1.1",  # IPv4 address
        "10.5",  # plain decimal
        "1E11.9",  # glued to a preceding digit
        "xE11.9",  # glued to a preceding letter
        "Node v18.17.1",  # version string with a second dot
        "Recorded e11.9 for the visit",  # codes must be uppercase
        "Using release v18.1 today",  # lowercase version string
        "a12.f3",  # lowercase hash fragment
        "C4B.0",  # not a letter-third category
    ],
)
def test_when_not_a_dotted_code_then_not_detected(text, recognizer, entities):
    """Shapes that are not dotted ICD-10-CM codes are ignored."""
    assert recognizer.analyze(text, entities) == []


def test_when_uppercase_lookalike_then_detected_at_weak_score(recognizer, entities):
    """An uppercase version number has the code shape. It stays weak."""
    results = recognizer.analyze("Using release V18.1 today", entities)

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.1)


def test_when_custom_name_and_entity_then_applied():
    """Loader keyword arguments reach the base class."""
    custom = UsIcd10CmRecognizer(name="CustomIcd", supported_entity="MY_DX")

    assert custom.name == "CustomIcd"
    assert custom.supported_entities == ["MY_DX"]


@pytest.fixture(scope="module")
def analyzer(spacy_nlp_engine):
    """Analyzer with only this recognizer registered."""
    registry = RecognizerRegistry()
    registry.add_recognizer(UsIcd10CmRecognizer())
    return AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )


def _results(analyzer, text):
    return [r for r in analyzer.analyze(text, language="en") if r.entity_type == ENTITY]


@pytest.mark.parametrize(
    "prefix",
    [
        "ICD-10 code:",
        "icd10:",
        "ICD-10-CM:",
        "Diagnosis:",
        "Diagnoses:",
        "Diagnosis code:",
    ],
)
def test_when_context_word_precedes_then_score_is_boosted(prefix, analyzer):
    """A diagnosis context word before the code raises the score."""
    results = _results(analyzer, f"{prefix} E11.9")

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.45)


def test_when_no_context_word_then_score_is_base_score(analyzer):
    """Without a context word the base score stands."""
    results = _results(analyzer, "Reading E11.9")

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.1)


def test_when_lowercase_version_after_context_word_then_not_detected(analyzer):
    """A context word does not turn a lowercase version string into a code."""
    assert _results(analyzer, "diagnosis of the crash: upgrade to v18.1") == []


def test_when_context_word_follows_then_score_not_boosted(analyzer):
    """Context after the match does not boost, by design."""
    results = _results(analyzer, "E11.9 is the diagnosis code")

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.1)


def test_when_enabled_in_yaml_then_loads_and_detects(tmp_path, spacy_nlp_engine):
    """The recognizer is reachable through the YAML path users configure."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: UsIcd10CmRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: us
"""
    )
    registry = RecognizerRegistryProvider(
        conf_file=str(conf)
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )

    results = analyzer.analyze("Diagnosis code E11.9 recorded", language="en")

    assert [r.entity_type for r in results] == [ENTITY]


def test_when_default_yaml_entry_then_disabled_and_loads_when_enabled():
    """The shipped entry exists once, is disabled and loads when enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "UsIcd10CmRecognizer"]
    assert len(entries) == 1
    assert entries[0]["enabled"] is False
    assert entries[0]["country_code"] == "us"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entries[0], enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["UsIcd10CmRecognizer"]


def test_when_built_directly_or_added_then_same_results(analyzer):
    """Direct use and registry use give the same result."""
    text = "Diagnosis E11.9 noted"
    direct = UsIcd10CmRecognizer().analyze(text, [ENTITY])
    via_registry = _results(analyzer, text)

    assert [(r.start, r.end) for r in direct] == [
        (r.start, r.end) for r in via_registry
    ]
