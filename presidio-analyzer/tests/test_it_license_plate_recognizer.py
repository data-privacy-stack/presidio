"""Tests for Italian license plate (IT_LICENSE_PLATE) recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import spacy
import yaml
from presidio_analyzer import AnalyzerEngine, Pattern
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NlpArtifacts, NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import ItLicensePlateRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests.mocks import NlpEngineMock

CAR_SCORE = 0.3
# Default LemmaContextAwareEnhancer boost: 0.3 + 0.35
CAR_SCORE_WITH_CONTEXT = 0.65
MOTORCYCLE_SCORE = 0.05
ENTITY = "IT_LICENSE_PLATE"


@pytest.fixture(scope="module")
def recognizer():
    """Create an ItLicensePlateRecognizer instance for testing."""
    return ItLicensePlateRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the IT_LICENSE_PLATE entity type for testing."""
    return [ENTITY]


@pytest.mark.parametrize(
    "text, expected_spans, expected_score",
    [
        # fmt: off
        # Car format, with and without separators
        ("AB123CD", [(0, 7)], CAR_SCORE),
        ("AB 123 CD", [(0, 9)], CAR_SCORE),
        ("AB-123-CD", [(0, 9)], CAR_SCORE),
        ("AA000AA", [(0, 7)], CAR_SCORE),
        ("ZZ999ZZ", [(0, 7)], CAR_SCORE),
        # Reserved series: trailers (X), local police (Y), square plates (Z)
        ("XA123BC", [(0, 7)], CAR_SCORE),
        ("YA 123 AB", [(0, 9)], CAR_SCORE),
        ("ZA 400 LV", [(0, 9)], CAR_SCORE),
        # Plates embedded in surrounding text
        ("Il veicolo targato FG 456 HJ risulta rubato.", [(19, 28)], CAR_SCORE),
        ("Targhe: GA123BC e EK-987-LM", [(8, 15), (18, 27)], CAR_SCORE),
        ("(targa: DX321YZ).", [(8, 15)], CAR_SCORE),
        # Motorcycle format
        ("AB12345", [(0, 7)], MOTORCYCLE_SCORE),
        ("AB 12345", [(0, 8)], MOTORCYCLE_SCORE),
        ("La moto targata EF 54321", [(16, 24)], MOTORCYCLE_SCORE),
        # fmt: on
    ],
)
def test_when_valid_plate_in_text_then_found_with_exact_span_and_score(
    text, expected_spans, expected_score, recognizer, entities
):
    results = sorted(recognizer.analyze(text, entities), key=lambda r: r.start)
    assert [(r.start, r.end) for r in results] == expected_spans
    for result in results:
        assert result.entity_type == ENTITY
        assert result.score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "text",
    [
        # Letters I, O, Q, U are never used on car plates
        "AI123CD",
        "OB123CD",
        "AB123QD",
        "AB123CU",
        # Lowercase text: plates are issued in capital letters
        "ab123cd",
        "ab12345",
        # Lookalikes: ordinary Italian text and codes of the same shape
        "Codice articolo IQ 500 OU",
        "Sono da 120 km da casa",
        "Il veicolo costa da 15000 euro",
        "IL 10000",
        "IO12345",
        # Wrong number of letters or digits
        "AB12CD",
        "AB1234CD",
        "A123CD",
        "ABC123DE",
        "AB123CDE",
        "AB1234",
        "AB123456",
        # Not a standalone token
        "XAB123CD",
        "AB123CD9",
        "12AB123CD",
        # Unsupported separators
        "AB.123.CD",
        "AB  123  CD",
        # Unrelated text
        "ciao mondo",
        "1234567",
    ],
)
def test_when_text_is_not_a_plate_then_nothing_found(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


def _nlp_artifacts(text: str) -> NlpArtifacts:
    """Tokenize Italian text without a trained model; lemmas are lowercase.

    The mock engine is needed so that NlpArtifacts extracts keywords, which
    the context enhancer reads; punctuation is excluded as a real engine would.
    """
    doc = spacy.blank("it")(text)
    punctuation = [token.text for token in doc if token.is_punct]
    return NlpArtifacts(
        entities=[],
        tokens=doc,
        tokens_indices=[token.idx for token in doc],
        lemmas=[token.text.lower() for token in doc],
        nlp_engine=NlpEngineMock(punct_words=punctuation),
        language="it",
    )


@pytest.mark.parametrize(
    "text, expect_boost",
    [
        # fmt: off
        ("Il veicolo targato FG456HJ è fermo", True),
        ("Targa: FG456HJ", True),
        ("Immatricolazione FG456HJ", True),
        # Compounds are covered by substring matching of the base word
        ("L'autoveicolo FG456HJ", True),
        ("Autovettura immatricolata FG456HJ", True),
        # Context is prefix-only by default: a word after the match does not count
        ("FG456HJ è la targa", False),
        ("Il codice è FG456HJ", False),
        # Short words that are deliberately not context words
        ("L'autorizzazione FG456HJ", False),
        ("Accesso remoto FG456HJ", False),
        # fmt: on
    ],
)
def test_when_context_word_precedes_plate_then_score_is_boosted(
    text, expect_boost, recognizer, entities
):
    nlp_artifacts = _nlp_artifacts(text)
    raw = recognizer.analyze(text, entities, nlp_artifacts)
    assert len(raw) == 1
    assert raw[0].score == pytest.approx(CAR_SCORE)

    enhanced = LemmaContextAwareEnhancer().enhance_using_context(
        text=text,
        raw_results=raw,
        nlp_artifacts=nlp_artifacts,
        recognizers=[recognizer],
    )
    assert len(enhanced) == 1
    if expect_boost:
        assert enhanced[0].score == pytest.approx(CAR_SCORE_WITH_CONTEXT)
    else:
        assert enhanced[0].score == pytest.approx(CAR_SCORE)


def test_when_custom_patterns_and_context_given_then_they_override_defaults():
    custom = ItLicensePlateRecognizer(
        patterns=[Pattern("custom (strong)", r"\bTARGA\d{3}\b", 0.9)],
        context=["prova"],
    )
    results = custom.analyze("TARGA123 AB123CD", [ENTITY])
    assert [(r.start, r.end) for r in results] == [(0, 8)]
    assert results[0].score == pytest.approx(0.9)
    assert custom.context == ["prova"]


def test_when_enabled_in_default_yaml_then_loads_and_detects():
    """Detection must work through the path users actually configure.

    The recognizer only supports Italian, so the registry configuration must
    list ``it`` among its top-level ``supported_languages``.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "ItLicensePlateRecognizer"]
    assert len(entries) == 1, "ItLicensePlateRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "it"
    assert entry["enabled"] is False
    assert entry["supported_languages"] == ["it"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["it"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == [
        "ItLicensePlateRecognizer"
    ]

    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "it", "model_name": "no_op"}]),
        supported_languages=["it"],
    )
    text = "Il veicolo targato FG 456 HJ risulta rubato."
    results = analyzer.analyze(text, language="it")

    assert [(r.entity_type, r.start, r.end) for r in results] == [(ENTITY, 19, 28)]
    assert results[0].score == pytest.approx(CAR_SCORE)


def test_when_registry_languages_exclude_italian_then_recognizer_not_loaded():
    """The shipped top-level default is English-only, which filters this out."""
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "ItLicensePlateRecognizer",
                    "supported_languages": ["it"],
                    "type": "predefined",
                    "enabled": True,
                    "country_code": "it",
                }
            ],
        }
    ).create_recognizer_registry()
    assert registry.recognizers == []
