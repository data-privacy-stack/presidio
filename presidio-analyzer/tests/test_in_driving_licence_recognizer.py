import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import InDrivingLicenceRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return InDrivingLicenceRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_DRIVING_LICENCE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # Valid: no separators
        ("MH1420200001234", 1, (0, 15), 0.3),
        # Valid: hyphen separators
        ("MH-14-20200001234", 1, (0, 17), 0.3),
        # Valid: space separators
        ("HR 06 19850034761", 1, (0, 17), 0.3),
        # Valid: embedded in text with exact boundaries
        ("My driving licence number is KA 01 20150012345 issued in Bangalore", 1, (29, 46), 0.3),
        # Valid: old state code (Orissa -> Odisha)
        ("OR1220000001111", 1, (0, 15), 0.3),
        # Valid: union territory
        ("DL-01-20180045678", 1, (0, 17), 0.3),
        # Invalid: unknown state code
        ("XX1420200001234", 0, (), ()),
        # Invalid: year before 1950
        ("MH1419400001234", 0, (), ()),
        # Invalid: too short
        ("MH142020000123", 0, (), ()),
        # Invalid: too long
        ("MH142020000012345", 0, (), ()),
        # Lookalike negative: 15-digit number that is not a licence
        ("AB1299991234567", 0, (), ()),
        # fmt: on
    ],
)
def test_when_driving_licence_in_text_then_found(
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


def test_context_words_boost_score(recognizer, entities):
    """Score should be higher with context words than without."""
    text_without_context = "MH1420200001234"
    text_with_context = "driving licence MH1420200001234"

    results_without = recognizer.analyze(text_without_context, entities)
    results_with = recognizer.analyze(text_with_context, entities)

    assert len(results_without) == 1
    assert len(results_with) == 1
    assert results_with[0].score > results_without[0].score


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
    """Detection must work through the path users actually configure."""
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: InDrivingLicenceRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: in
"""
    )
    registry = RecognizerRegistryProvider(
        conf_file=conf
    ).create_recognizer_registry()

    nlp_engine = NlpEngineProvider().create_engine()
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)

    results = analyzer.analyze(
        "My driving licence is MH1420200001234", language="en"
    )

    entity_types = [r.entity_type for r in results]
    assert "IN_DRIVING_LICENCE" in entity_types
