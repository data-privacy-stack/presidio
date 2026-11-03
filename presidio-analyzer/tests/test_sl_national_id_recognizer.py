"""Tests for Sri Lanka national identity card (NIC) recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import SlNationalIdRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Create a Sri Lanka NIC recognizer instance for testing."""
    return SlNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Sri Lanka NIC entity type for testing."""
    return ["LK_NATIONAL_ID"]


# Fixtures are synthetic numbers built to the published structures
# (12-digit: birth year + day of year + serial + check digit,
# old form: 2-digit birth year + day of year + serial + check digit + V/X),
# because the recognizer implements no checksum: no authoritative source
# describes a check digit algorithm for the Sri Lanka NIC (see the
# recognizer docstring).
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid IDs, 12-digit form (since 2016) ---
        ("199212304567", 1, (0, 12), 0.5),
        ("200162389012", 1, (0, 12), 0.5),
        (
            "His NIC 199212304567 was verified",
            1,
            (8, 20),
            0.5,
        ),
        # day 366 is valid in a leap year (1992)
        ("199236604567", 1, (0, 12), 0.5),
        # female day 866 (366 after the 500 offset) in a leap year
        ("199286604567", 1, (0, 12), 0.5),
        # --- Valid IDs, old form (9 digits + V/X) ---
        ("921234567V", 1, (0, 10), 0.55),
        ("926234567x", 1, (0, 10), 0.55),
        (
            "Her NIC 926234567x is old",
            1,
            (8, 18),
            0.55,
        ),
        # --- Invalid: day of year out of range (sanity check) ---
        ("199299904567", 0, (0, 0), 0),
        ("199200004567", 0, (0, 0), 0),
        ("199240004567", 0, (0, 0), 0),
        ("199286704567", 0, (0, 0), 0),
        # day 366 in a non-leap year (1991)
        ("199136604567", 0, (0, 0), 0),
        # old form, day 999
        ("929994567V", 0, (0, 0), 0),
        # --- Invalid: birth year out of range (sanity check) ---
        ("189912304567", 0, (0, 0), 0),
        ("203512304567", 0, (0, 0), 0),
        # --- Invalid: wrong digit counts ---
        ("19921230456", 0, (0, 0), 0),
        ("1992123045678", 0, (0, 0), 0),
        ("92123456V", 0, (0, 0), 0),
        ("9212345678V", 0, (0, 0), 0),
        # --- Invalid: wrong trailing letter ---
        ("921234567Z", 0, (0, 0), 0),
        # --- Invalid: all digits identical (sanity check) ---
        ("111111111111", 0, (0, 0), 0),
        # --- Lookalikes: same shape, but not a national ID ---
        ("Order number 19921230456701 was shipped", 0, (0, 0), 0),
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
        "IDs: 921234567V and 199212304567", entities
    )

    assert len(results) == 2
    assert_result(results[0], entities[0], 5, 15, 0.55)
    assert_result(results[1], entities[0], 20, 32, 0.5)


sequential_test_set = [
    ["234567890", True],
    ["321098765", True],
    ["199212304", False],
    ["921234567", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential digit run check used on the ID digits."""
    assert SlNationalIdRecognizer._is_sequential(input_text) == expected_output


day_of_year_test_set = [
    # (full year, day code, expected)
    [1992, 123, True],  # male, leap year
    [1991, 366, False],  # day 366 needs a leap year
    [1992, 366, True],  # day 366 in a leap year
    [2001, 623, True],  # female: 623 - 500 = 123
    [1992, 866, True],  # female: 866 - 500 = 366, leap year
    [1991, 866, False],  # female day 366 in a non-leap year
    [1992, 0, False],
    [1992, 400, False],  # 367-500 is never valid
    [1992, 999, False],
]


@pytest.mark.parametrize(
    "full_year, day_code, expected_output", day_of_year_test_set
)
def test_valid_day_of_year(full_year, day_code, expected_output):
    """Test the calendar check on the day of the year part."""
    assert (
        SlNationalIdRecognizer._valid_day_of_year(full_year, day_code)
        == expected_output
    )


def test_invalidate_result(recognizer):
    """Sanity checks reject trivial numbers and accept real ID shapes."""
    assert recognizer.invalidate_result("199212304567") is False
    assert recognizer.invalidate_result("200162389012") is False
    assert recognizer.invalidate_result("199236604567") is False
    assert recognizer.invalidate_result("199286604567") is False
    assert recognizer.invalidate_result("921234567V") is False
    assert recognizer.invalidate_result("926234567x") is False
    assert recognizer.invalidate_result("199299904567") is True
    assert recognizer.invalidate_result("199200004567") is True
    assert recognizer.invalidate_result("199240004567") is True
    assert recognizer.invalidate_result("199286704567") is True
    assert recognizer.invalidate_result("199136604567") is True
    assert recognizer.invalidate_result("203512304567") is True
    assert recognizer.invalidate_result("111111111111") is True
    assert recognizer.invalidate_result("111111111V") is True
    assert recognizer.invalidate_result("921234567Z") is True
    assert recognizer.invalidate_result("1992123045") is True


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "nic",
        "national identity card",
        "sri lanka",
        "sri lankan",
        "identity card",
        "drp",
        "registration of persons",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["LK_NATIONAL_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = SlNationalIdRecognizer(name="CustomSlNationalId")
    assert recognizer.name == "CustomSlNationalId"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around a Sri Lanka NIC raises its pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(SlNationalIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="199212304567", language="en", entities=["LK_NATIONAL_ID"]
    )
    with_context = analyzer.analyze(
        text="199212304567",
        language="en",
        entities=["LK_NATIONAL_ID"],
        context=["nic"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.5
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_context_does_not_rescue_invalid_id(mock_nlp_engine):
    """A context word never rescues a number the sanity checks reject."""
    registry = RecognizerRegistry()
    registry.add_recognizer(SlNationalIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    results = analyzer.analyze(
        text="NIC 199299904567",
        language="en",
        entities=["LK_NATIONAL_ID"],
    )
    assert results == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "SlNationalIdRecognizer"]
    assert len(entries) == 1, "SlNationalIdRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "lk"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "SlNationalIdRecognizer"
    ]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "LK_NATIONAL_ID" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My NIC is 199212304567",
        language="en",
        entities=["LK_NATIONAL_ID"],
    )
    assert [result.entity_type for result in results] == ["LK_NATIONAL_ID"]
