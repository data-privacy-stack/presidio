"""Tests for Egypt national ID recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import EgNationalIdRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Create an Egypt national ID recognizer instance for testing."""
    return EgNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Egypt national ID entity type for testing."""
    return ["EG_NATIONAL_ID"]


# Fixtures are synthetic numbers built to the published 14-digit structure
# (century digit 2 or 3 + birth date + governorate code + serial + one
# digit), because the recognizer implements no checksum: the check digit
# algorithm is not published in an authoritative source. The only public
# Luhn claim found (a SlideShare deck) contradicts its own worked example,
# and an independent validator package calls the mechanism "undisclosed"
# (see the recognizer docstring).
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid IDs (weak pattern, 14 continuous digits) ---
        ("29005170148235", 1, (0, 14), 0.3),
        ("30112021573982", 1, (0, 14), 0.3),
        (
            "The egyptian id 29005170148235 was verified",
            1,
            (16, 30),
            0.3,
        ),
        # --- Invalid: century digit other than 2 or 3 ---
        ("19005170148235", 0, (0, 0), 0),
        ("49005170148235", 0, (0, 0), 0),
        # --- Invalid: wrong digit counts ---
        ("2900517014823", 0, (0, 0), 0),
        ("290051701482350", 0, (0, 0), 0),
        # --- Invalid: month part out of range (sanity check) ---
        ("29013011748235", 0, (0, 0), 0),
        ("29000011748235", 0, (0, 0), 0),
        # --- Invalid: day part out of range (sanity check) ---
        ("29005321748235", 0, (0, 0), 0),
        ("29005001748235", 0, (0, 0), 0),
        # --- Invalid: all digits identical (sanity check) ---
        ("22222222222222", 0, (0, 0), 0),
        ("33333333333333", 0, (0, 0), 0),
        # --- Invalid: fully sequential runs (sanity check) ---
        ("23456789012345", 0, (0, 0), 0),
        ("32109876543210", 0, (0, 0), 0),
        # --- Lookalikes: same shape, but not a national ID ---
        ("Order number 2900517014823501 was shipped", 0, (0, 0), 0),
        ("abcdefghijklmn", 0, (0, 0), 0),
        # fmt: on
    ],
)
def test_when_national_id_in_text_then_all_ids_found(
    text, expected_len, expected_position, expected_score, recognizer, entities
):
    """Test that the recognizer finds valid IDs and rejects invalid ones."""
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
    """Both IDs in one text are found at their exact positions."""
    results = recognizer.analyze(
        "IDs: 29005170148235 and 30112021573982", entities
    )

    assert len(results) == 2
    assert_result(results[0], entities[0], 5, 19, 0.3)
    assert_result(results[1], entities[0], 24, 38, 0.3)


sequential_test_set = [
    ["23456789012345", True],
    ["32109876543210", True],
    ["29005170148235", False],
    ["30112021573982", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential digit run check used on the full ID."""
    assert EgNationalIdRecognizer._is_sequential(input_text) == expected_output


def test_invalidate_result(recognizer):
    """Sanity checks reject trivial numbers and accept real ID shapes."""
    assert recognizer.invalidate_result("29005170148235") is False
    assert recognizer.invalidate_result("30112021573982") is False
    assert recognizer.invalidate_result("19005170148235") is True
    assert recognizer.invalidate_result("29013011748235") is True
    assert recognizer.invalidate_result("29005321748235") is True
    assert recognizer.invalidate_result("22222222222222") is True
    assert recognizer.invalidate_result("23456789012345") is True
    assert recognizer.invalidate_result("2900517014823") is True


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "national id",
        "national identity",
        "egyptian id",
        "egypt",
        "national number",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["EG_NATIONAL_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = EgNationalIdRecognizer(name="CustomEgNationalId")
    assert recognizer.name == "CustomEgNationalId"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around a national ID raises its pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(EgNationalIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="29005170148235", language="en", entities=["EG_NATIONAL_ID"]
    )
    with_context = analyzer.analyze(
        text="29005170148235",
        language="en",
        entities=["EG_NATIONAL_ID"],
        context=["national id"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.3
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_context_does_not_rescue_invalid_id(mock_nlp_engine):
    """A context word never rescues a number the sanity checks reject."""
    registry = RecognizerRegistry()
    registry.add_recognizer(EgNationalIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    results = analyzer.analyze(
        text="Egyptian ID 23456789012345",
        language="en",
        entities=["EG_NATIONAL_ID"],
    )
    assert results == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "EgNationalIdRecognizer"]
    assert len(entries) == 1, "EgNationalIdRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "eg"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "EgNationalIdRecognizer"
    ]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "EG_NATIONAL_ID" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My national id is 29005170148235",
        language="en",
        entities=["EG_NATIONAL_ID"],
    )
    assert [result.entity_type for result in results] == ["EG_NATIONAL_ID"]
