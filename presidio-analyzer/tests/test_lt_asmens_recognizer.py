"""Tests for Lithuanian personal code (asmens kodas) recognizer."""

import datetime
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import LtAsmensRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Create a Lithuanian personal code recognizer for testing."""
    return LtAsmensRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Lithuanian personal code entity type for testing."""
    return ["LT_ASMENS"]


# Fixtures are synthetic numbers whose check digits were
# computed with the pinned two round mod 11 check,
# except for 33309240064 (the OECD Lithuania TIN
# sheet worked example) and 38409152012 (the
# MicroFocus example). No fixture is a real
# person's number beyond those published examples.
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid personal codes ---
        # synthetic numbers, check digits computed with the two round check
        ("33309240064", 1, (0, 11), 0.5),  # male 1933-09-24, s006, sum1 109, 2nd 169
        ("10101010005", 1, (0, 11), 0.5),  # male 1801-01-01, s000, sum 16, check 5
        ("38409152012", 1, (0, 11), 0.5),  # male 1984-09-15, s201, sum 134, check 2
        ("38503031230", 1, (0, 11), 0.5),  # male 1985-03-03, s123, sum 99, check 0
        ("60002290003", 1, (0, 11), 0.5),  # female, leap day 2000-02-29, sum 91
        ("50001010006", 1, (0, 11), 0.5),  # male 2000-01-01, s000, sum 17, check 6
        ("19912310008", 1, (0, 11), 0.5),  # male 1899-12-31, s000, sum 85, check 8
        ("29912310009", 1, (0, 11), 0.5),  # female 1899-12-31, s000, sum 86, check 9
        ("45409065730", 1, (0, 11), 0.5),  # female 1954-09-06, s573, both rounds 10
        ("61507151237", 1, (0, 11), 0.5),  # female 2015-07-15, s123, sum 128, check 7
        # a number embedded in a sentence
        ("Asmens kodas 33309240064 on file", 1, (13, 24), 0.5),
        ("Asmens kodas 38409152012", 1, (13, 24), 0.5),
        # a sentence period after the check digit does not block the match
        ("Asmens kodas 33309240064.", 1, (13, 24), 0.5),
        # --- Invalid: wrong check digit ---
        ("33309240065", 0, (0, 0), 0),
        ("10101010006", 0, (0, 0), 0),
        ("38409152013", 0, (0, 0), 0),
        ("60002290004", 0, (0, 0), 0),
        # --- Invalid: first digit 7, 8, 9 or 0 ---
        # each carries a valid checksum and a real date; stdnum accepts 7, 8, 9
        ("73309240063", 0, (0, 0), 0),  # first digit 7, 2100 century
        ("83309240064", 0, (0, 0), 0),  # first digit 8, 2100 century
        ("93309240065", 0, (0, 0), 0),  # first digit 9, unknown birth date
        ("03309240067", 0, (0, 0), 0),  # first digit 0
        # --- Invalid: impossible birth date ---
        ("33302300068", 0, (0, 0), 0),  # 30 Feb 1933
        ("40002290001", 0, (0, 0), 0),  # 29 Feb 1900, not a leap year
        ("33313310062", 0, (0, 0), 0),  # month 13
        ("33301000067", 0, (0, 0), 0),  # day 00
        ("33300010069", 0, (0, 0), 0),  # month 00
        # --- Invalid: future birth date ---
        ("52701010009", 0, (0, 0), 0),  # 1 Jan 2027, stdnum accepts, rejected here
        # --- Invalid: all digits identical ---
        ("00000000000", 0, (0, 0), 0),  # passes the checksum, rejected as implausible
        ("11111111111", 0, (0, 0), 0),
        ("99999999999", 0, (0, 0), 0),
        # --- Invalid: fully sequential digit runs ---
        ("01234567890", 0, (0, 0), 0),
        ("98765432109", 0, (0, 0), 0),
        ("12345678901", 0, (0, 0), 0),
        ("87654321098", 0, (0, 0), 0),  # passes the checksum, rejected as sequential
        # --- Invalid: wrong lengths ---
        ("3330924006", 0, (0, 0), 0),  # 10 digits
        ("333092400644", 0, (0, 0), 0),  # 12 digits
        # --- Lookalikes: same shape, but not a personal code ---
        ("133309240064", 0, (0, 0), 0),  # a leading digit
        ("A33309240064", 0, (0, 0), 0),  # a leading letter
        ("33309240064A", 0, (0, 0), 0),  # a trailing letter
        ("3330 9240 064", 0, (0, 0), 0),  # spaced form, stdnum accepts, not matched
        ("3330-9240-064", 0, (0, 0), 0),  # dashed form, not matched
        # fmt: on
    ],
)
def test_when_asmens_in_text_then_all_ids_found(
    text, expected_len, expected_position, expected_score, recognizer, entities
):
    """Test that the recognizer finds valid numbers and rejects invalid ones."""
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
    """Both personal codes in one text are found."""
    results = recognizer.analyze("Asmens kodas: 33309240064 and 38409152012", entities)

    assert len(results) == 2
    assert_result(results[0], entities[0], 14, 25, 0.5)
    assert_result(results[1], entities[0], 30, 41, 0.5)


sequential_test_set = [
    ["01234567890", True],
    ["98765432109", True],
    ["12345678901", True],
    ["87654321098", True],
    ["33309240064", False],
    ["38409152012", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential run check used on the number digits."""
    assert LtAsmensRecognizer._is_sequential(input_text) == expected_output


def test_check_digit(recognizer):
    """The check digit matches the published worked examples."""
    assert recognizer._check_digit("3330924006") == "4"
    assert recognizer._check_digit("1010101000") == "5"
    assert recognizer._check_digit("3840915201") == "2"
    assert recognizer._check_digit("3850303123") == "0"
    assert recognizer._check_digit("6000229000") == "3"
    assert recognizer._check_digit("5000101000") == "6"
    assert recognizer._check_digit("1991231000") == "8"
    assert recognizer._check_digit("2991231000") == "9"
    assert recognizer._check_digit("6150715123") == "7"
    # both rounds leave remainder 10, so the check digit is 0
    assert recognizer._check_digit("4540906573") == "0"


def test_has_valid_checksum(recognizer):
    """The two round mod 11 check accepts valid numbers and rejects the rest."""
    assert recognizer._has_valid_checksum("33309240064") is True
    assert recognizer._has_valid_checksum("10101010005") is True
    assert recognizer._has_valid_checksum("38409152012") is True
    assert recognizer._has_valid_checksum("38503031230") is True
    assert recognizer._has_valid_checksum("60002290003") is True
    assert recognizer._has_valid_checksum("50001010006") is True
    assert recognizer._has_valid_checksum("45409065730") is True
    assert recognizer._has_valid_checksum("33309240065") is False
    assert recognizer._has_valid_checksum("10101010006") is False
    assert recognizer._has_valid_checksum("38409152013") is False
    assert recognizer._has_valid_checksum("60002290004") is False


def test_has_valid_birth_date(recognizer):
    """The birth date rule accepts real past dates and rejects the rest."""
    assert recognizer._has_valid_birth_date("33309240064") is True
    assert recognizer._has_valid_birth_date("10101010005") is True
    assert recognizer._has_valid_birth_date("38409152012") is True
    assert recognizer._has_valid_birth_date("60002290003") is True
    assert recognizer._has_valid_birth_date("19912310008") is True
    assert recognizer._has_valid_birth_date("33302300068") is False
    assert recognizer._has_valid_birth_date("40002290001") is False
    assert recognizer._has_valid_birth_date("33313310062") is False
    assert recognizer._has_valid_birth_date("33301000067") is False
    assert recognizer._has_valid_birth_date("33300010069") is False


def test_future_birth_date_is_rejected(recognizer, entities):
    """A number with tomorrow as its birth date is never detected."""
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    body = f"5{tomorrow.year % 100:02d}{tomorrow.month:02d}{tomorrow.day:02d}000"
    number = body + recognizer._check_digit(body)
    assert recognizer.analyze(number, entities) == []


def test_invalidate_result_rules(recognizer):
    """Each structural rule rejects its own case directly."""
    assert recognizer.invalidate_result("33309240064") is False
    assert recognizer.invalidate_result("10101010005") is False
    assert recognizer.invalidate_result("38409152012") is False
    assert recognizer.invalidate_result("60002290003") is False
    assert recognizer.invalidate_result("45409065730") is False
    assert recognizer.invalidate_result("33309240065") is True
    assert recognizer.invalidate_result("73309240063") is True
    assert recognizer.invalidate_result("83309240064") is True
    assert recognizer.invalidate_result("93309240065") is True
    assert recognizer.invalidate_result("03309240067") is True
    assert recognizer.invalidate_result("33302300068") is True
    assert recognizer.invalidate_result("40002290001") is True
    assert recognizer.invalidate_result("52701010009") is True
    assert recognizer.invalidate_result("00000000000") is True
    assert recognizer.invalidate_result("11111111111") is True
    assert recognizer.invalidate_result("99999999999") is True
    assert recognizer.invalidate_result("01234567890") is True
    assert recognizer.invalidate_result("87654321098") is True
    assert recognizer.invalidate_result("3330924006") is True
    assert recognizer.invalidate_result("333092400644") is True


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = LtAsmensRecognizer(name="CustomLtAsmens")
    assert recognizer.name == "CustomLtAsmens"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around a number raises its pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(LtAsmensRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(text="33309240064", language="en", entities=["LT_ASMENS"])
    with_context = analyzer.analyze(
        text="33309240064",
        language="en",
        entities=["LT_ASMENS"],
        context=["asmens kodas"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.5
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_context_does_not_rescue_invalid_id(mock_nlp_engine):
    """A context word never rescues a number the checksum rejects."""
    registry = RecognizerRegistry()
    registry.add_recognizer(LtAsmensRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    results = analyzer.analyze(
        text="asmens kodas 33309240065",
        language="en",
        entities=["LT_ASMENS"],
    )
    assert results == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "LtAsmensRecognizer"]
    assert len(entries) == 1, "LtAsmensRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "lt"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["LtAsmensRecognizer"]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "LT_ASMENS" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My asmens kodas is 33309240064",
        language="en",
        entities=["LT_ASMENS"],
    )
    assert [result.entity_type for result in results] == ["LT_ASMENS"]


def test_registered_disabled_in_subset_yamls():
    """Recognizer is listed with enabled false in the subset YAMLs."""
    analyzer_dir = Path(presidio_analyzer.__file__).parent
    repo_root = analyzer_dir.parents[1]
    yaml_paths = [
        analyzer_dir / "conf" / "slim.yaml",
        analyzer_dir / "conf" / "default_analyzer_full.yaml",
        repo_root / "e2e-tests" / "resources" / "test_ollama_enabled_recognizers.yaml",
    ]
    for yaml_path in yaml_paths:
        content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        recognizers = content.get("recognizers")
        if recognizers is None:
            recognizers = content["recognizer_registry"]["recognizers"]
        entries = [r for r in recognizers if r.get("name") == "LtAsmensRecognizer"]
        assert len(entries) == 1, f"LtAsmensRecognizer missing from {yaml_path}"
        assert entries[0]["enabled"] is False, (
            f"LtAsmensRecognizer enabled in {yaml_path}"
        )
