import pytest
import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.predefined_recognizers import NlBsnRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests.mocks import NlpEngineMock

BARE_SCORE = 0.05
GROUPED_SCORE = 0.1


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the NlBsnRecognizer."""
    return NlBsnRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return entities to analyze."""
    return ["NL_BSN"]


# All numbers are synthetic and built to pass (or fail) the eleven test.
@pytest.mark.parametrize(
    "text, expected_positions, expected_score",
    [
        ("123456782", [(0, 9)], BARE_SCORE),
        ("111222333", [(0, 9)], BARE_SCORE),
        # Issued as eight digits, written with a leading zero.
        ("012345672", [(0, 9)], BARE_SCORE),
        # Embedded in a sentence.
        ("Mijn nummer is 123456782, graag bewaren.", [(15, 24)], BARE_SCORE),
        # Grouped forms, with a consistent separator.
        ("1234.56.782", [(0, 11)], GROUPED_SCORE),
        ("1234 56 782", [(0, 11)], GROUPED_SCORE),
        # Two numbers in one text.
        ("123456782 en 111222333", [(0, 9), (13, 22)], BARE_SCORE),
    ],
)
def test_when_valid_bsn_then_detected_at_pattern_score(
    text, expected_positions, expected_score, recognizer, entities
):
    results = sorted(recognizer.analyze(text, entities), key=lambda r: r.start)

    assert [(r.start, r.end) for r in results] == expected_positions
    for result in results:
        assert result.entity_type == "NL_BSN"
        assert result.score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "text",
    [
        # Fails the eleven test.
        "123456783",
        # Lookalike: a valid old Dutch bank account number. It passes the bank
        # eleven test (last weight +1) but not the BSN one (last weight -1).
        "Rekeningnummer 123456789",
        # All zeros pass the eleven test arithmetically but are not a BSN.
        "000000000",
        # Wrong length, or part of a longer number.
        "12345678",
        "1234567820",
        # Mixed separators in the grouped form.
        "1234.56 782",
    ],
)
def test_when_not_a_bsn_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("123456782", None),
        ("1234.56.782", None),
        ("123456783", False),
        ("123456789", False),
        ("12345678", False),
    ],
)
def test_validate_result(text, expected, recognizer):
    assert recognizer.validate_result(text) is expected


def _enhance(recognizer, text):
    nlp = spacy.blank("nl")
    doc = nlp(text)
    artifacts = NlpArtifacts(
        entities=[],
        tokens=doc,
        tokens_indices=[token.idx for token in doc],
        lemmas=[token.text.lower() for token in doc],
        nlp_engine=NlpEngineMock(punct_words=[":"]),
        language="nl",
    )
    raw = recognizer.analyze(text, recognizer.supported_entities, artifacts)
    return LemmaContextAwareEnhancer().enhance_using_context(
        text=text,
        raw_results=raw,
        nlp_artifacts=artifacts,
        recognizers=[recognizer],
    )


def test_when_context_word_precedes_then_score_rises(recognizer):
    enhancer = LemmaContextAwareEnhancer()
    with_context = _enhance(recognizer, "Burgerservicenummer: 123456782")
    with_short_context = _enhance(recognizer, "BSN 123456782")
    without_context = _enhance(recognizer, "Ordernummer 123456782")

    # The enhancer adds the similarity factor, but never goes below its floor.
    expected = max(
        BARE_SCORE + enhancer.context_similarity_factor,
        enhancer.min_score_with_context_similarity,
    )
    assert with_context[0].score == pytest.approx(expected)
    assert with_short_context[0].score == pytest.approx(expected)
    assert without_context[0].score == pytest.approx(BARE_SCORE)


def test_when_context_word_follows_then_score_unchanged(recognizer):
    # Context is prefix-only by default.
    results = _enhance(recognizer, "123456782 is mijn BSN")

    assert results[0].score == pytest.approx(BARE_SCORE)


class _DutchNlpEngineMock(NlpEngineMock):
    def __init__(self):
        super().__init__(nlp_artifacts=NlpArtifacts([], [], [], [], None, "nl", []))

    def get_supported_languages(self):
        return ["nl"]


def test_when_enabled_in_yaml_then_loads_and_detects(tmp_path):
    """Detection must work through the path users actually configure.

    The recognizer is Dutch only, so the top-level supported_languages must
    include "nl" or the registry filters it out silently.
    """
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - nl
recognizers:
  - name: NlBsnRecognizer
    supported_languages:
      - nl
    type: predefined
    enabled: true
    country_code: nl
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=_DutchNlpEngineMock(),
        supported_languages=["nl"],
    )

    results = analyzer.analyze("Nummer 123456782", language="nl")

    assert [(r.entity_type, r.start, r.end) for r in results] == [("NL_BSN", 7, 16)]
    assert results[0].score == pytest.approx(BARE_SCORE)


def test_when_default_configuration_then_not_loaded():
    """Country-specific recognizers ship disabled in the default configuration."""
    registry = RecognizerRegistryProvider().create_recognizer_registry()

    assert "NlBsnRecognizer" not in {type(r).__name__ for r in registry.recognizers}
