import datetime
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import InDrivingLicenceRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return InDrivingLicenceRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_DRIVING_LICENCE"]


CURRENT_YEAR = datetime.date.today().year


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # valid: no separator, space, hyphen, both separators
        ("MH1420110062821", 1, (0, 15), 0.3),
        ("MH14 20110062821", 1, (0, 16), 0.3),
        ("HR-0619850034761", 1, (0, 16), 0.3),
        ("MH-14-20110062821", 1, (0, 17), 0.3),
        # lowercase input
        ("mh1420110062821", 1, (0, 15), 0.3),
        # Telangana's 2024 code and a legacy code
        ("TG0920240001234", 1, (0, 15), 0.3),
        ("OR0219990012345", 1, (0, 15), 0.3),
        # year boundaries
        ("KA0119500001234", 1, (0, 15), 0.3),
        (f"KA01{CURRENT_YEAR}0001234", 1, (0, 15), 0.3),
        # inside a sentence: no surrounding space or punctuation included
        ("My licence is KA0120190001234 and it expires soon.", 1, (14, 29), 0.3),
        ("Holder KA01 20190001234, issued in Bengaluru.", 1, (7, 23), 0.3),
        # invalid state code
        ("ZZ1420110062821", 0, (), ()),
        ("XY-0619850034761", 0, (), ()),
        # invalid year
        ("MH1419490062821", 0, (), ()),
        ("MH1400000062821", 0, (), ()),
        (f"MH14{CURRENT_YEAR + 1}0062821", 0, (), ()),
        # wrong length
        ("MH142011006282", 0, (), ()),
        ("MH14201100628210", 0, (), ()),
        ("MH14 2011006282", 0, (), ()),
        # extra letter in front of the state code
        ("XMH1420110062821", 0, (), ()),
        # digits only
        ("142011006282134", 0, (), ()),
        ("1420110062821", 0, (), ()),
        # lookalike: same shape, but a non-Indian two-letter prefix
        ("Order TX1520231234567 shipped", 0, (), ()),
        # fmt: on
    ],
)
def test_when_driving_licence_in_text_then_all_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)

    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )


@pytest.fixture(scope="module")
def analyzer(spacy_nlp_engine):
    registry = RecognizerRegistry()
    registry.add_recognizer(InDrivingLicenceRecognizer())
    return AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)


def test_when_context_before_number_then_score_raised(analyzer, entities):
    results = analyzer.analyze(
        "Driving licence number: MH14 20110062821", language="en", entities=entities
    )

    assert len(results) == 1
    assert (results[0].start, results[0].end) == (24, 40)
    assert results[0].score == pytest.approx(0.65)


def test_when_no_context_then_base_score(analyzer, entities):
    results = analyzer.analyze(
        "Reference MH14 20110062821", language="en", entities=entities
    )

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.3)


def test_when_context_after_number_then_score_not_raised(analyzer, entities):
    # Context is matched on the words before the entity only (prefix count 5).
    results = analyzer.analyze(
        "MH14 20110062821 is my driving licence", language="en", entities=entities
    )

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.3)


def test_accepts_name_kwarg():
    recognizer = InDrivingLicenceRecognizer(name="CustomInDrivingLicence")
    assert recognizer.name == "CustomInDrivingLicence"


def test_loads_and_detects_when_enabled_in_default_yaml(spacy_nlp_engine):
    """Detection must work through the path users actually configure."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "InDrivingLicenceRecognizer"]
    assert len(entries) == 1, "InDrivingLicenceRecognizer missing from YAML"
    entry = entries[0]
    assert entry["enabled"] is False
    assert entry["country_code"] == "in"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == [
        "InDrivingLicenceRecognizer"
    ]

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)
    results = analyzer.analyze("DL no: HR-0619850034761", language="en")

    assert [result.entity_type for result in results] == ["IN_DRIVING_LICENCE"]
    assert (results[0].start, results[0].end) == (7, 23)
