"""Tests for Ghana Card Personal Identification Number recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import GhGhanaCardRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Create a Ghana Card recognizer instance for testing."""
    return GhGhanaCardRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Ghana Card entity type for testing."""
    return ["GH_GHANA_CARD"]


# Fixtures are synthetic numbers built to the published structure
# (GHA, 9 digits, check digit; some early cards show 8 digits),
# because the recognizer implements no checksum: no authoritative
# source describes a check digit algorithm for the Ghana Card (see the
# recognizer docstring).
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid PINs, 9-digit system number ---
        ("GHA-482913657-0", 1, (0, 15), 0.5),
        ("GHA-987654321-4", 1, (0, 15), 0.5),
        (
            "Her Ghana Card GHA-482913657-0 was verified",
            1,
            (15, 30),
            0.5,
        ),
        # lowercase prefix is accepted
        ("gha-482913657-0", 1, (0, 15), 0.5),
        # --- Valid PINs, 8-digit system number (early cards) ---
        ("GHA-28471935-6", 1, (0, 14), 0.5),
        (
            "Card GHA-28471935-6 on file",
            1,
            (5, 19),
            0.5,
        ),
        # --- Invalid: wrong digit counts ---
        ("GHA-1234567-9", 0, (0, 0), 0),
        ("GHA-1234567890-1", 0, (0, 0), 0),
        ("GHA-482913657-01", 0, (0, 0), 0),
        # --- Invalid: all digits identical (sanity check) ---
        ("GHA-111111111-1", 0, (0, 0), 0),
        ("GHA-000000000-0", 0, (0, 0), 0),
        # --- Invalid: fully sequential runs (sanity check) ---
        ("GHA-234567890-1", 0, (0, 0), 0),
        ("GHA-987654321-0", 0, (0, 0), 0),
        # --- Lookalikes: same shape, wrong prefix or separators ---
        ("GHA123456789-0", 0, (0, 0), 0),
        ("GHA 123456789 0", 0, (0, 0), 0),
        ("KEN-123456789-0", 0, (0, 0), 0),
        ("abcdefghij", 0, (0, 0), 0),
        # fmt: on
    ],
)
def test_when_ghana_card_in_text_then_all_ids_found(
    text, expected_len, expected_position, expected_score, recognizer, entities
):
    """Test that the recognizer finds valid PINs and rejects invalid ones."""
    results = recognizer.analyze(text, entities)

    assert len(results) == expected_len
    if expected_len > 0:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )


def test_multiple_ids_positions(recognizer, entities):
    """Both PINs in one text are found at their exact positions."""
    results = recognizer.analyze(
        "Cards: GHA-482913657-0 and GHA-987654321-4", entities
    )

    assert len(results) == 2
    assert_result(results[0], entities[0], 7, 22, 0.5)
    assert_result(results[1], entities[0], 27, 42, 0.5)


sequential_test_set = [
    ["2345678901", True],
    ["3210987654", True],  # descent wraps 0 to 9 and continues
    ["9876543210", True],
    ["1357924680", False],
    ["123456780", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential digit run check used on the PIN digits."""
    assert GhGhanaCardRecognizer._is_sequential(input_text) == expected_output


def test_invalidate_result(recognizer):
    """Sanity checks reject trivial numbers and accept real PIN shapes."""
    assert recognizer.invalidate_result("GHA-482913657-0") is False
    assert recognizer.invalidate_result("GHA-987654321-4") is False
    assert recognizer.invalidate_result("GHA-28471935-6") is False
    assert recognizer.invalidate_result("gha-482913657-0") is False
    assert recognizer.invalidate_result("GHA-111111111-1") is True
    assert recognizer.invalidate_result("GHA-000000000-0") is True
    assert recognizer.invalidate_result("GHA-234567890-1") is True
    assert recognizer.invalidate_result("GHA-1234567-9") is True
    assert recognizer.invalidate_result("GHA-1234567890-1") is True
    assert recognizer.invalidate_result("GHA-482913657-01") is True
    assert recognizer.invalidate_result("KEN-123456789-0") is True


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "ghana",
        "ghana card",
        "ghanaian",
        "nia",
        "national identification authority",
        "personal identification number",
        "ecowas identity card",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["GH_GHANA_CARD"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = GhGhanaCardRecognizer(name="CustomGhGhanaCard")
    assert recognizer.name == "CustomGhGhanaCard"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around a Ghana Card PIN raises its pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(GhGhanaCardRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="GHA-482913657-0", language="en", entities=["GH_GHANA_CARD"]
    )
    with_context = analyzer.analyze(
        text="GHA-482913657-0",
        language="en",
        entities=["GH_GHANA_CARD"],
        context=["ghana card"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.5
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_context_does_not_rescue_invalid_id(mock_nlp_engine):
    """A context word never rescues a number the sanity checks reject."""
    registry = RecognizerRegistry()
    registry.add_recognizer(GhGhanaCardRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    results = analyzer.analyze(
        text="Ghana Card GHA-111111111-1",
        language="en",
        entities=["GH_GHANA_CARD"],
    )
    assert results == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "GhGhanaCardRecognizer"]
    assert len(entries) == 1, "GhGhanaCardRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "gh"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "GhGhanaCardRecognizer"
    ]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "GH_GHANA_CARD" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="Ghana Card GHA-482913657-0",
        language="en",
        entities=["GH_GHANA_CARD"],
    )
    assert len(results) == 1
    assert results[0].entity_type == "GH_GHANA_CARD"
