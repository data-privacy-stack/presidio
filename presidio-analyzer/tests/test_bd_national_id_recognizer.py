"""Tests for Bangladesh national ID (NID) recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import BdNationalIdRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Create a Bangladesh NID recognizer instance for testing."""
    return BdNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Bangladesh NID entity type for testing."""
    return ["BD_NATIONAL_ID"]


# Fixtures are synthetic numbers built to the published structures
# (17-digit: birth year + district + RMO + upazila + union + serial,
# 13-digit: the same without the birth year prefix, 10-digit smart NID),
# because the recognizer implements no checksum: no authoritative source
# describes a check digit algorithm for the Bangladesh NID (see the
# recognizer docstring).
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid IDs, 17-digit form (birth year prefix) ---
        ("19884512345123456", 1, (0, 17), 0.55),
        ("20011203456789012", 1, (0, 17), 0.55),
        (
            "The NID 19884512345123456 was verified",
            1,
            (8, 25),
            0.55,
        ),
        # --- Valid IDs, 13-digit form (older cards) ---
        ("4512345123456", 1, (0, 13), 0.4),
        ("1203456789012", 1, (0, 13), 0.4),
        (
            "The NID 4512345123456 was verified",
            1,
            (8, 21),
            0.4,
        ),
        # --- Valid IDs, 10-digit form (smart NID) ---
        ("5839201746", 1, (0, 10), 0.3),
        ("7913580246", 1, (0, 10), 0.3),
        # --- Invalid: birth year out of range (sanity check) ---
        ("20304512345123456", 0, (0, 0), 0),
        ("18994512345123456", 0, (0, 0), 0),
        # --- Invalid: district code out of range (sanity check) ---
        ("19880012345123456", 0, (0, 0), 0),
        ("19889912345123456", 0, (0, 0), 0),
        ("0012345123456", 0, (0, 0), 0),
        ("9912345123456", 0, (0, 0), 0),
        # --- Invalid: wrong digit counts ---
        ("583920174", 0, (0, 0), 0),
        ("58392017461", 0, (0, 0), 0),
        ("583920174612", 0, (0, 0), 0),
        ("45123451234567", 0, (0, 0), 0),
        ("1988451234512345", 0, (0, 0), 0),
        # --- Invalid: all digits identical (sanity check) ---
        ("11111111111111111", 0, (0, 0), 0),
        ("5555555555", 0, (0, 0), 0),
        # --- Invalid: fully sequential runs (sanity check) ---
        ("12345678901234567", 0, (0, 0), 0),
        ("1234567890123", 0, (0, 0), 0),
        ("1234567890", 0, (0, 0), 0),
        # --- Lookalikes: same shape, but not a national ID ---
        ("Order number 1988451234512345601 was shipped", 0, (0, 0), 0),
        ("abcdefghij", 0, (0, 0), 0),
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
        "IDs: 4512345123456 and 5839201746", entities
    )

    assert len(results) == 2
    assert_result(results[0], entities[0], 5, 18, 0.4)
    assert_result(results[1], entities[0], 23, 33, 0.3)


sequential_test_set = [
    ["12345678901234567", True],
    ["32109876543210987", True],
    ["19884512345123456", False],
    ["4512345123456", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential digit run check used on the full ID."""
    assert BdNationalIdRecognizer._is_sequential(input_text) == expected_output


def test_invalidate_result(recognizer):
    """Sanity checks reject trivial numbers and accept real ID shapes."""
    assert recognizer.invalidate_result("19884512345123456") is False
    assert recognizer.invalidate_result("4512345123456") is False
    assert recognizer.invalidate_result("5839201746") is False
    assert recognizer.invalidate_result("20304512345123456") is True
    assert recognizer.invalidate_result("19880012345123456") is True
    assert recognizer.invalidate_result("0012345123456") is True
    assert recognizer.invalidate_result("583920174") is True


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "nid",
        "national id",
        "national identity",
        "bangladesh",
        "smart card",
        "voter id",
        "birth registration",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["BD_NATIONAL_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = BdNationalIdRecognizer(name="CustomBdNationalId")
    assert recognizer.name == "CustomBdNationalId"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around a Bangladesh NID raises its pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(BdNationalIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="4512345123456", language="en", entities=["BD_NATIONAL_ID"]
    )
    with_context = analyzer.analyze(
        text="4512345123456",
        language="en",
        entities=["BD_NATIONAL_ID"],
        context=["nid"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.4
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_context_does_not_rescue_invalid_id(mock_nlp_engine):
    """A context word never rescues a number the sanity checks reject."""
    registry = RecognizerRegistry()
    registry.add_recognizer(BdNationalIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    results = analyzer.analyze(
        text="NID 20304512345123456",
        language="en",
        entities=["BD_NATIONAL_ID"],
    )
    assert results == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "BdNationalIdRecognizer"]
    assert len(entries) == 1, "BdNationalIdRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "bd"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "BdNationalIdRecognizer"
    ]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "BD_NATIONAL_ID" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My NID is 19884512345123456",
        language="en",
        entities=["BD_NATIONAL_ID"],
    )
    assert [result.entity_type for result in results] == ["BD_NATIONAL_ID"]
