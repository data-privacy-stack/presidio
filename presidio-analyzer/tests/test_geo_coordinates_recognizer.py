import time
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import GeoCoordinatesRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

ENTITY = "GEO_COORDINATES"


@pytest.fixture(scope="module")
def recognizer():
    return GeoCoordinatesRecognizer()


@pytest.fixture(scope="module")
def entities():
    return [ENTITY]


@pytest.mark.parametrize(
    "text, match, score",
    [
        # fmt: off
        # Decimal degrees pair (weak)
        ("40.7128, -74.0060", "40.7128, -74.0060", 0.2),
        ("Located at 40.7128, -74.0060 today", "40.7128, -74.0060", 0.2),
        ("40.7128,-74.0060", "40.7128,-74.0060", 0.2),
        ("+40.7128, +74.0060", "+40.7128, +74.0060", 0.2),
        ("-33.86882, 151.20929", "-33.86882, 151.20929", 0.2),
        ("[40.71280000, -74.00600000]", "40.71280000, -74.00600000", 0.2),
        ("Fix at 40.7128, -74.0060.", "40.7128, -74.0060", 0.2),
        ("90.0000, 180.0000", "90.0000, 180.0000", 0.2),
        ("−33.8688, 151.2093", "−33.8688, 151.2093", 0.2),
        ("40.7128, −74.0060", "40.7128, −74.0060", 0.2),
        # Decimal degrees with hemisphere (medium)
        ("40.4461° N, 79.9822° W", "40.4461° N, 79.9822° W", 0.4),
        ("Pittsburgh is at 40.4461N 79.9822W", "40.4461N 79.9822W", 0.4),
        ("40.45 S, 79.98 E", "40.45 S, 79.98 E", 0.4),
        # Degrees, minutes and seconds (strong)
        ("40°26'46\"N 79°58'56\"W", "40°26'46\"N 79°58'56\"W", 0.6),
        ("40° 26′ 46″ N, 79° 58′ 56″ W", "40° 26′ 46″ N, 79° 58′ 56″ W", 0.6),
        ("40°26'N 79°58'W", "40°26'N 79°58'W", 0.6),
        ("40°26'46.5\"N 79°58'56.25\"W", "40°26'46.5\"N 79°58'56.25\"W", 0.6),
        ("90°00'00\"N 180°00'00\"E", "90°00'00\"N 180°00'00\"E", 0.6),
        # geo URI (strong)
        ("geo:40.7128,-74.0060", "geo:40.7128,-74.0060", 0.6),
        ("Open geo:40.7128,-74.0060,10;u=35 now", "geo:40.7128,-74.0060,10;u=35", 0.6),
        # fmt: on
    ],
)
def test_when_coordinates_then_detected_with_exact_score_and_bounds(
    text, match, score, recognizer, entities
):
    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    start = text.index(match)
    assert (results[0].start, results[0].end) == (start, start + len(match))
    assert results[0].entity_type == ENTITY
    assert results[0].score == pytest.approx(score)


def test_when_two_coordinates_in_text_then_both_detected(recognizer, entities):
    text = "From 40.7128, -74.0060 to 34.0522, -118.2437"

    results = recognizer.analyze(text, entities)

    assert [text[r.start : r.end] for r in results] == [
        "40.7128, -74.0060",
        "34.0522, -118.2437",
    ]


@pytest.mark.parametrize(
    "text",
    [
        # fmt: off
        "91.12345, 10.12345",  # latitude out of range
        "45.12345, 181.12345",  # longitude out of range
        "12.50, 13.75",  # prices and measurements: too few decimals
        "192.168.1.1",  # IPv4 address
        "v1.2.3, 4.5.6",  # version strings
        "0.0000, 0.0000",  # null island placeholder
        "40°75'00\"N 79°58'56\"W",  # minutes above 59
        "40°26'61\"N 79°58'56\"W",  # seconds above 59
        "91°00'00\"N 79°58'56\"W",  # latitude degrees out of range
        "90°30'00\"N 79°58'56\"W",  # past the pole
        "40°75'00\"n 79°58'56\"w",  # minutes above 59, lowercase letters
        "40°00'00\"N 180°30'00\"E",  # past the antimeridian
        "90°30'00\"n 79°58'56\"w",  # past the pole, lowercase letters
        "40°26'46\"n 79°58'56\"w",  # hemisphere letters must be uppercase
        "12.50 s, 30.25 w",  # hemisphere letters must be uppercase
        "40.4461n 79.9822w",  # hemisphere letters must be uppercase
        "0°00'00\"N 0°00'00\"E",  # null island placeholder in DMS
        "geo:95.0,10.0",  # geo URI latitude out of range
        "geo:0,0",  # geo URI null island
        "40.7128 -74.0060",  # no comma between bare decimals
        "40.7128, -74.00600000123",  # too many fractional digits
        "40.7128,\n-74.0060",  # a pair does not span two lines
        # fmt: on
    ],
)
def test_when_not_coordinates_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


@pytest.mark.parametrize(
    "text",
    [
        '{"lat": 40.7128, "lng": -74.0060}',  # keyed JSON values
        "+40.7128-074.0060/",  # compact ISO 6709 string
        "4807.038,N,01131.000,E",  # NMEA sentence fields
    ],
)
def test_when_notation_is_not_supported_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


def test_when_lookalike_pair_has_valid_shape_then_scores_weak(recognizer, entities):
    # Mathematical constants have the same shape as coordinates. They are
    # detected at the weak score so that a threshold can filter them.
    results = recognizer.analyze("3.14159, 2.71828", entities)

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.2)


@pytest.mark.parametrize(
    "text",
    [
        "1.11" + " " * 100_000 + "x",
        "1.11 N" + " " * 100_000,
        "40°26'N" + " " * 100_000,
    ],
)
def test_when_long_run_of_whitespace_then_fast(text, recognizer, entities):
    start = time.perf_counter()
    results = recognizer.analyze(text, entities)

    assert time.perf_counter() - start < 5.0
    assert results == []


def test_when_custom_name_and_entity_then_applied():
    custom = GeoCoordinatesRecognizer(name="CustomGeo", supported_entity="MY_GEO")

    assert custom.name == "CustomGeo"
    assert custom.supported_entities == ["MY_GEO"]


@pytest.fixture(scope="module")
def analyzer(spacy_nlp_engine):
    registry = RecognizerRegistry()
    registry.add_recognizer(GeoCoordinatesRecognizer())
    return AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )


def _geo_results(analyzer, text):
    return [r for r in analyzer.analyze(text, language="en") if r.entity_type == ENTITY]


@pytest.mark.parametrize(
    "prefix",
    [
        "latitude and longitude:",
        "longitude:",
        "coordinate:",
        "coordinates:",
        "geolocation:",
        "gps:",
        "lat/long:",
        "lat long",
    ],
)
def test_when_context_word_precedes_then_score_is_boosted(prefix, analyzer):
    results = _geo_results(analyzer, f"{prefix} 40.7128, -74.0060")

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.55)


def test_when_similar_word_precedes_then_score_not_boosted(analyzer):
    results = _geo_results(analyzer, "Project coordinator: 3.14159, 2.71828")

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.2)


def test_when_no_context_word_then_score_is_base_score(analyzer):
    results = _geo_results(analyzer, "Reading 40.7128, -74.0060")

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.2)


def test_when_context_word_follows_then_score_not_boosted(analyzer):
    results = _geo_results(analyzer, "40.7128, -74.0060 are the coordinates")

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.2)


def test_when_enabled_in_yaml_then_loads_and_detects(tmp_path, spacy_nlp_engine):
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: GeoCoordinatesRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
"""
    )
    registry = RecognizerRegistryProvider(
        conf_file=str(conf)
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )

    results = analyzer.analyze("Fix at 40.4461° N, 79.9822° W", language="en")

    assert [r.entity_type for r in results] == [ENTITY]


def test_when_default_yaml_entry_then_disabled_by_default_and_loads_when_enabled():
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "GeoCoordinatesRecognizer"]
    assert len(entries) == 1
    assert entries[0]["enabled"] is False

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entries[0], enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "GeoCoordinatesRecognizer"
    ]


def test_when_built_directly_or_added_or_loaded_then_same_results(analyzer):
    text = "Meet at geo:40.7128,-74.0060"
    direct = GeoCoordinatesRecognizer().analyze(text, [ENTITY])
    via_registry = _geo_results(analyzer, text)

    assert [(r.start, r.end, r.score) for r in direct] == [
        (r.start, r.end, r.score) for r in via_registry
    ]
