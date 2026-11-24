import unicodedata
from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import InAadhaarRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from tests import assert_result
from tests.india_digit_scripts import (
    INDIC_DIGIT_BLOCKS,
    NON_INDIC_DIGIT_BLOCKS,
    to_script,
)


@pytest.fixture(scope="module")
def recognizer() -> InAadhaarRecognizer:
    return InAadhaarRecognizer()


@pytest.fixture(scope="module")
def entities() -> list[str]:
    return ["IN_AADHAAR"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        ("123456789012", 0, (0,12), 0),
        ("312345678909", 1, (0, 12), 1),
        ("399876543211", 1, (0, 12), 1),
        ("1234 5678 9012", 0, (0,14), 0),
        ("3123 4567 8909", 1, (0, 14), 1),
        ("3998 7654 3211", 1, (0, 14), 1),
        ("1234-5678-9012", 0, (0,14), 0),
        ("3123-4567-8909", 1, (0, 14), 1),
        ("3998-7654-3211", 1, (0, 14), 1),
        ("1234:5678:9012", 0, (0,14), 0),
        ("3123:4567:8909", 1, (0, 14), 1),
        ("3998:7654:3211", 1, (0, 14), 1),
        ("My Aadhaar number is 400123456787 with a lot of text beyond it", 1, (21,33), 1),
        # fmt: on
    ],
)
def test_when_aadhaar_in_text_then_all_aadhaars_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
) -> None:
    results = recognizer.analyze(text, entities)
    print(results)

    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )

palindrome_test_set = [
    ["abMA", False, False],
    ["abCba", False, True],
    ["ABBA", False, True],
    ["aBba", True, True],
    ["NotAPalindrome", True, False],
]


@pytest.mark.parametrize(
    "input_text,case_sensitive, expected_output", palindrome_test_set
)
def test_is_palindrome(input_text, case_sensitive, expected_output):
    """
    Test if input is a true palindrome as defined in base class.

    :param input_text: input text to validate
    :param case_sensitive: flag to calculate palindrome with no case
    :param expected_output: calculated output
    :return: True/False
    """
    assert (
            InAadhaarRecognizer._is_palindrome(input_text, case_sensitive)
            == expected_output
    )


verhoeff_test_set = [
    [312345678909, True],
    [400123456787, True],
    [123456789012, False],
]

@pytest.mark.parametrize("input_number, is_verhoeff", verhoeff_test_set)
def test_is_verhoeff(input_number, is_verhoeff) -> None:
    """
    Test to assert verhoeff number validation based on checksum from base class.

    :param input_number: input integer
    :param is_verhoeff: expected flag
    :return: True/False
    """
    assert InAadhaarRecognizer._is_verhoeff_number(input_number) == is_verhoeff


def test_the_indic_digit_blocks_hold_the_digits_of_their_script():
    """Guard the test data: each block must start at the digit zero."""
    for script, zero in INDIC_DIGIT_BLOCKS.items():
        assert unicodedata.name(chr(zero)) == f"{script.upper()} DIGIT ZERO"


@pytest.mark.parametrize("script, zero", list(INDIC_DIGIT_BLOCKS.items()))
def test_when_aadhaar_written_in_an_indic_script_then_detected(
    script,
    zero,
    recognizer,
    entities,
):
    """The same identifier must be found whichever script writes its digits."""
    aadhaar = to_script("312345678909", zero)
    text = f"My Aadhaar number is {aadhaar} with a lot of text beyond it"

    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert_result(results[0], entities[0], 21, 33, 1)


@pytest.mark.parametrize("script, zero", list(INDIC_DIGIT_BLOCKS.items()))
def test_when_separated_aadhaar_written_in_an_indic_script_then_detected(
    script,
    zero,
    recognizer,
    entities,
):
    """The separated form must be recognised in every Indic script too."""
    aadhaar = to_script("3123 4567 8909", zero)
    text = f"My Aadhaar number is {aadhaar}"

    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert_result(results[0], entities[0], 21, 35, 1)


@pytest.mark.parametrize("script, zero", list(INDIC_DIGIT_BLOCKS.items()))
def test_when_indic_aadhaar_fails_the_checksum_then_not_detected(
    script,
    zero,
    recognizer,
    entities,
):
    """The Verhoeff checksum must still reject a bad number in any script."""
    aadhaar = to_script("123456789012", zero)
    text = f"My Aadhaar number is {aadhaar}"

    assert recognizer.analyze(text, entities) == []


@pytest.mark.parametrize("script, zero", list(NON_INDIC_DIGIT_BLOCKS.items()))
def test_when_digits_are_not_from_an_indic_script_then_not_detected(
    script,
    zero,
    recognizer,
    entities,
):
    """Thai, Arabic-Indic and fullwidth digits are not used for Indian ids."""
    aadhaar = to_script("312345678909", zero)
    text = f"My Aadhaar number is {aadhaar}"

    assert recognizer.analyze(text, entities) == []


def test_when_the_same_aadhaar_is_written_in_two_scripts_then_both_match(
    recognizer,
    entities,
):
    """The script of the digits must not move the entity or change its score."""
    ascii_result = recognizer.analyze(
        "My Aadhaar number is 312345678909", entities
    )[0]
    indic_result = recognizer.analyze(
        "My Aadhaar number is " + to_script("312345678909", 0x0966), entities
    )[0]

    assert (ascii_result.start, ascii_result.end) == (indic_result.start, indic_result.end)
    assert ascii_result.score == indic_result.score


def test_when_context_word_present_then_score_is_unchanged(
    spacy_nlp_engine,
    recognizer,
    entities,
):
    """The checksum already pins the score, so context cannot raise it."""
    analyzer = AnalyzerEngine(
        registry=RecognizerRegistry(recognizers=[recognizer]),
        nlp_engine=spacy_nlp_engine,
    )

    with_context = analyzer.analyze(
        "My Aadhaar number is 312345678909", language="en"
    )
    without_context = analyzer.analyze(
        "Reference 312345678909 was filed.", language="en"
    )

    assert with_context[0].score == 1
    assert without_context[0].score == 1


def test_recognizer_is_registered_in_the_default_yaml():
    """Users reach this recognizer by enabling it in the shipped YAML."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "InAadhaarRecognizer"]

    assert len(entries) == 1, "InAadhaarRecognizer missing from YAML"
    assert entries[0]["country_code"] == "in"
    assert entries[0]["enabled"] is False


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
    """Detection must work through the path users actually configure."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: InAadhaarRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: in
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    analyzer = AnalyzerEngine(registry=registry)

    results = analyzer.analyze("My Aadhaar number is 312345678909", language="en")

    assert [result.entity_type for result in results] == ["IN_AADHAAR"]
