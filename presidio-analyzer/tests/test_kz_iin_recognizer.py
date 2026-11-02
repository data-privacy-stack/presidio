"""Tests for Kazakhstan Individual Identification Number (IIN) recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import KzIinRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Create a Kazakhstan IIN recognizer instance for testing."""
    return KzIinRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Kazakhstan IIN entity type for testing."""
    return ["KZ_IIN"]


# Fixtures are synthetic numbers built to the published structure
# (YYMMDD birth date + gender/century digit + 4-digit serial + check
# digit), because the recognizer implements no checksum: no
# authoritative Kazakh source with a worked valid example was found
# for the published check digit algorithm (see the recognizer
# docstring). The trailing digit in each fixture is arbitrary.
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid IINs ---
        # male, born 1990-07-01 (digit 3 = male, 1900s)
        ("900701312345", 1, (0, 12), 0.5),
        # female, born 1995-12-31 (digit 4 = female, 1900s)
        ("951231498765", 1, (0, 12), 0.5),
        (
            "His IIN 900701312345 was verified",
            1,
            (8, 20),
            0.5,
        ),
        # day 29 Feb is valid in a leap year (2000, digit 5 = male, 2000s)
        ("000229500123", 1, (0, 12), 0.5),
        # 1800s century digit (digit 1 = male, 1800s)
        ("900701112345", 1, (0, 12), 0.5),
        # --- Invalid: month or day out of range (sanity check) ---
        ("901301312345", 0, (0, 0), 0),  # month 13
        ("900231312345", 0, (0, 0), 0),  # 31 Feb
        ("900700312345", 0, (0, 0), 0),  # month 00
        ("900701002345", 0, (0, 0), 0),  # day 00
        # day 29 Feb in a non-leap year (2001, digit 6 = female, 2000s)
        ("010229600123", 0, (0, 0), 0),
        # --- Invalid: century/gender digit out of range ---
        ("900701712345", 0, (0, 0), 0),  # digit 7
        ("900701012345", 0, (0, 0), 0),  # digit 0
        # --- Invalid: serial number 0000 ---
        ("900701300005", 0, (0, 0), 0),
        # --- Invalid: birth date in the future ---
        ("990701512345", 0, (0, 0), 0),  # 2099-07-01
        # --- Invalid: wrong digit counts ---
        ("90070131234", 0, (0, 0), 0),  # 11 digits
        ("9007013123456", 0, (0, 0), 0),  # 13 digits
        # --- Invalid: all digits identical (sanity check) ---
        ("111111111111", 0, (0, 0), 0),
        # --- Lookalikes: same shape, but not an IIN ---
        ("Order number 90070131234501 was shipped", 0, (0, 0), 0),
        ("abcdefghij", 0, (0, 0), 0),
        # fmt: on
    ],
)
def test_when_iin_in_text_then_all_ids_found(
    text, expected_len, expected_position, expected_score, recognizer, entities
):
    """Test that the recognizer finds valid IINs and rejects invalid ones."""
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
    """Both IINs in one text are found at their exact positions."""
    results = recognizer.analyze(
        "IDs: 900701312345 and 951231498765", entities
    )

    assert len(results) == 2
    assert_result(results[0], entities[0], 5, 17, 0.5)
    assert_result(results[1], entities[0], 22, 34, 0.5)


sequential_test_set = [
    ["234567890123", True],
    ["321098765432", True],
    ["900701312345", False],
    ["951231498765", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential digit run check used on the IIN digits."""
    assert KzIinRecognizer._is_sequential(input_text) == expected_output


birth_date_test_set = [
    # (iin, expected)
    ["900701312345", True],  # 1990-07-01, male 1900s
    ["951231498765", True],  # 1995-12-31, female 1900s
    ["000229500123", True],  # 2000-02-29, leap year
    ["010229600123", False],  # 2001-02-29, not a leap year
    ["901301312345", False],  # month 13
    ["900231312345", False],  # 31 Feb
    ["990701512345", False],  # 2099, in the future
    ["900701712345", False],  # century digit 7
]


@pytest.mark.parametrize("input_text, expected_output", birth_date_test_set)
def test_valid_birth_date(input_text, expected_output):
    """Test the calendar check on the birth date part."""
    assert KzIinRecognizer._valid_birth_date(input_text) == expected_output


def test_invalidate_result(recognizer):
    """Sanity checks reject trivial numbers and accept real IIN shapes."""
    assert recognizer.invalidate_result("900701312345") is False
    assert recognizer.invalidate_result("951231498765") is False
    assert recognizer.invalidate_result("000229500123") is False
    assert recognizer.invalidate_result("900701112345") is False
    assert recognizer.invalidate_result("901301312345") is True
    assert recognizer.invalidate_result("900231312345") is True
    assert recognizer.invalidate_result("010229600123") is True
    assert recognizer.invalidate_result("900701712345") is True
    assert recognizer.invalidate_result("900701300005") is True
    assert recognizer.invalidate_result("990701512345") is True
    assert recognizer.invalidate_result("111111111111") is True
    assert recognizer.invalidate_result("90070131234") is True


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "kazakhstan",
        "kazakh",
        "iin",
        "individual identification number",
        "zhsn",
        "national identification",
        "kazakhstani",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["KZ_IIN"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = KzIinRecognizer(name="CustomKzIin")
    assert recognizer.name == "CustomKzIin"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around a Kazakhstan IIN raises its pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(KzIinRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="900701312345", language="en", entities=["KZ_IIN"]
    )
    with_context = analyzer.analyze(
        text="900701312345",
        language="en",
        entities=["KZ_IIN"],
        context=["iin"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.5
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_context_does_not_rescue_invalid_id(mock_nlp_engine):
    """A context word never rescues a number the sanity checks reject."""
    registry = RecognizerRegistry()
    registry.add_recognizer(KzIinRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    results = analyzer.analyze(
        text="IIN 901301312345",
        language="en",
        entities=["KZ_IIN"],
    )
    assert results == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "KzIinRecognizer"]
    assert len(entries) == 1, "KzIinRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "kz"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "KzIinRecognizer"
    ]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "KZ_IIN" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My IIN is 900701312345",
        language="en",
        entities=["KZ_IIN"],
    )
    assert [result.entity_type for result in results] == ["KZ_IIN"]
