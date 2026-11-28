"""Tests for the Malaysian SSM registration number recognizer."""

import time
from datetime import date
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.predefined_recognizers.country_specific.malaysia import (
    MySsmRecognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

# All numbers below are synthetic.

NEXT_YEAR = date.today().year + 1


@pytest.fixture(scope="module")
def recognizer():
    return MySsmRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["MY_SSM"]


def _found(recognizer, entities, text):
    results = sorted(recognizer.analyze(text, entities), key=lambda r: r.start)
    for result in results:
        assert result.entity_type == "MY_SSM"
    return [(r.start, r.end, r.score) for r in results]


@pytest.mark.parametrize(
    "text, expected",
    [
        # 12-digit format: a valid number keeps its pattern score
        ("201901000005", [(0, 12, 0.4)]),
        ("SSM 202403123456.", [(4, 16, 0.4)]),
        # Every entity type code
        ("202001123456", [(0, 12, 0.4)]),  # 01 local company
        ("202002123456", [(0, 12, 0.4)]),  # 02 foreign company
        ("202003123456", [(0, 12, 0.4)]),  # 03 business
        ("202004123456", [(0, 12, 0.4)]),  # 04 local LLP
        ("202005123456", [(0, 12, 0.4)]),  # 05 foreign LLP
        ("202006123456", [(0, 12, 0.4)]),  # 06 professional practice LLP
        # Companies registered long before 2019 also have a 12-digit number
        ("196501000123", [(0, 12, 0.4)]),
        ("190003000001", [(0, 12, 0.4)]),
        # LLPs exist from 2012 (Act 743)
        ("201204000001", [(0, 12, 0.4)]),
        # Old company format, alone and in brackets after the name
        ("123456-X", [(0, 8, 0.1)]),
        ("1-A", [(0, 3, 0.1)]),
        ("1234567-K", [(0, 9, 0.1)]),
        ("Example Trading (643792-K) Kuala Lumpur", [(17, 25, 0.1)]),
        ("Example Trading ( 643792-K )", [(18, 26, 0.1)]),
        # Two numbers in one text
        ("201901000005 / 123456-X", [(0, 12, 0.4), (15, 23, 0.1)]),
        # Invalid entity type code
        ("202000123456", []),
        ("202007123456", []),
        ("202099123456", []),
        # LLP type before 2012
        ("201104000001", []),
        ("199905123456", []),
        ("200006123456", []),
        # Year out of range
        ("189901000001", []),
        ("210001000001", []),
        (f"{NEXT_YEAR}01000001", []),
        # Part of a longer number or token
        ("1201901000005", []),
        ("2019010000051", []),
        ("12345678-X", []),
        ("123456-XY", []),
        ("A123456-X", []),
        ("123456-X-1", []),
        ("1-123456-X", []),
        ("123456-X1", []),
        # Wrong separator or letter
        ("123456X", []),
        ("123456_X", []),
        ("123456-1", []),
        ("123456-x", []),
        ("2019-01-000005", []),
    ],
)
def test_when_ssm_in_text_then_all_ssm_numbers_found(
    text, expected, recognizer, entities
):
    found = _found(recognizer, entities, text)
    assert [(s, e) for s, e, _ in found] == [(s, e) for s, e, _ in expected]
    for (_, _, score), (_, _, expected_score) in zip(found, expected):
        assert score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "text",
    [
        "Warisan Katering (115948-H) dokumen",
        "Water filter model (560578-W) out of stock",
        "product code 115948-H",
    ],
)
def test_old_format_without_context_keeps_low_score(text, recognizer, entities):
    # Brackets alone are not evidence: product and model codes look the same.
    found = _found(recognizer, entities, text)
    assert len(found) == 1
    assert found[0][2] < 0.4


@pytest.mark.parametrize(
    "number, invalid",
    [
        ("201901000005", False),
        ("201204000001", False),
        ("201104000001", True),
        ("202007123456", True),
        ("189901000001", True),
        (f"{NEXT_YEAR}01000001", True),
        ("20190100000", True),
        ("123456-X", None),
    ],
)
def test_invalidate_result(recognizer, number, invalid):
    assert recognizer.invalidate_result(number) is invalid


def test_current_year_is_accepted(recognizer, entities):
    text = f"{date.today().year}01000001"
    assert _found(recognizer, entities, text) == [(0, 12, 0.4)]


def test_entity_type_codes_match_ssm_list():
    assert MySsmRecognizer.ENTITY_TYPE_CODES == {f"0{n}" for n in range(1, 7)}
    assert MySsmRecognizer.LLP_TYPE_CODES < MySsmRecognizer.ENTITY_TYPE_CODES


@pytest.mark.parametrize(
    "word", ["ssm", "registration", "syarikat", "sdn", "bhd", "berhad", "plt"]
)
def test_context_word_is_supportive(recognizer, word):
    find = LemmaContextAwareEnhancer._find_supportive_word_in_context
    assert find([word], recognizer.context)


@pytest.mark.parametrize(
    "word",
    ["region", "cost", "phone", "process", "procedure", "problem", "robot", "no"],
)
def test_short_abbreviations_left_out_of_context(recognizer, word):
    # "reg", "co", "no", "roc" and "rob" are not context words: in the default
    # substring mode they would also match these ordinary words.
    find = LemmaContextAwareEnhancer._find_supportive_word_in_context
    assert find([word], recognizer.context) == ""


@pytest.mark.parametrize(
    "word, expected",
    [
        # "ssm" is kept although it also occurs in "assessment", "harassment"
        # and "businessman": it is the name of the registry and the most
        # common label next to the number. Context only raises numbers that
        # already passed validation.
        ("assessment", "ssm"),
        # No common English or Malay word contains "sdn", "bhd" or "plt".
        ("sudden", ""),
        ("abhorrent", ""),
        ("plot", ""),
    ],
)
def test_short_context_words_inside_other_words(recognizer, word, expected):
    find = LemmaContextAwareEnhancer._find_supportive_word_in_context
    assert find([word], recognizer.context) == expected


def test_context_has_single_words_only(recognizer):
    # Phrases never match: the default enhancer compares single tokens.
    assert all(" " not in word for word in recognizer.context)


@pytest.mark.parametrize(
    "text",
    [
        "1" * 100_000,
        "1-" * 50_000,
        "(" * 50_000 + "123456" * 10_000,
        "2019" * 25_000 + "-X",
    ],
)
def test_long_adversarial_input_is_fast(recognizer, entities, text):
    start = time.perf_counter()
    recognizer.analyze(text, entities)
    assert time.perf_counter() - start < 0.5


def _shipped_recognizers():
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    return yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]


def _shipped_entry():
    entries = [r for r in _shipped_recognizers() if r.get("name") == "MySsmRecognizer"]
    assert len(entries) == 1, "MySsmRecognizer missing from YAML"
    return entries[0]


def test_exported_from_predefined_recognizers():
    from presidio_analyzer import predefined_recognizers

    assert "MySsmRecognizer" in predefined_recognizers.__all__
    assert predefined_recognizers.MySsmRecognizer is MySsmRecognizer


def test_shipped_yaml_entry_is_disabled_country_specific():
    entry = _shipped_entry()
    assert entry["type"] == "predefined"
    assert entry["country_code"] == "my"
    assert entry["enabled"] is False
    assert entry["supported_languages"] == ["en"]


@pytest.fixture(scope="module")
def analyzer_from_yaml(spacy_nlp_engine):
    """Analyzer built the way users enable the recognizer: through YAML."""
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(_shipped_entry(), enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["MySsmRecognizer"]
    return AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )


@pytest.mark.parametrize(
    "text, expected_span, expected_score",
    [
        # No context: pattern score
        ("Reference 201901000005 attached", "201901000005", 0.4),
        ("Model (643792-K) in stock", "643792-K", 0.1),
        # Context before the number raises the score
        ("SSM 201901000005", "201901000005", 0.75),
        ("Company registration 202003123456", "202003123456", 0.75),
        ("Nombor pendaftaran syarikat 202003123456", "202003123456", 0.75),
        ("Contoh Sdn Bhd (643792-K)", "643792-K", 0.45),
        ("Contoh Enterprise 201903000123", "201903000123", 0.75),
        ("Contoh PLT 201304000001", "201304000001", 0.75),
        # Words left out of the context list do not raise the score
        ("Process 201901000005 again", "201901000005", 0.4),
        ("Problem 201901000005 again", "201901000005", 0.4),
        ("Region 201901000005 again", "201901000005", 0.4),
        ("Cost 643792-K again", "643792-K", 0.1),
        # Known, recorded: "ssm" is a substring of "assessment"
        ("Assessment 201901000005", "201901000005", 0.75),
        # Context is prefix-only by default: a word after the number does not count
        ("201901000005 is our SSM number", "201901000005", 0.4),
    ],
)
def test_yaml_enabled_recognizer_detects_with_context(
    analyzer_from_yaml, text, expected_span, expected_score
):
    results = analyzer_from_yaml.analyze(text, language="en", entities=["MY_SSM"])
    assert len(results) == 1
    result = results[0]
    assert text[result.start : result.end] == expected_span
    assert result.score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "text",
    [
        "SSM 201907000005",  # entity type 07 does not exist
        "SSM 201104000005",  # LLP before Act 743
        "SSM 189901000005",  # year before 1900
    ],
)
def test_yaml_enabled_recognizer_drops_invalid_number(analyzer_from_yaml, text):
    assert analyzer_from_yaml.analyze(text, language="en", entities=["MY_SSM"]) == []


def test_country_filter_keeps_malaysian_recognizer():
    """supported_countries ["my"] keeps MySsm and drops other countries' recognizers."""
    by_name = {r.get("name"): r for r in _shipped_recognizers()}
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "supported_countries": ["my"],
            "recognizers": [
                dict(by_name["MySsmRecognizer"], enabled=True),
                dict(by_name["SgFinRecognizer"], enabled=True),
            ],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["MySsmRecognizer"]
