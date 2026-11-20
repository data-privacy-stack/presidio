from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import InPanRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from tests import assert_result
from tests.india_digit_scripts import (
    INDIC_DIGIT_BLOCKS,
    NON_INDIC_DIGIT_BLOCKS,
    to_script,
)


@pytest.fixture(scope="module")
def recognizer():
    return InPanRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_PAN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        ("AAASA1111R", 1, (0,10), 0.1) ,
        ("ABCPD1234Z", 1, (0, 10), 0.5),
        ("ABCND1234Z", 1, (0, 10), 0.1),
        ("A1111DFSFS", 1, (0,10),0.01),
        ("ABCD1234",0,(),(),),
        ("My PAN number is ABBPM4567S with a lot of text beyond it", 1, (17,27),.5),
        # fmt: on
    ],
)
def test_when_pan_in_text_then_all_pans_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
):
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


@pytest.mark.parametrize("script, zero", list(INDIC_DIGIT_BLOCKS.items()))
def test_when_pan_written_in_an_indic_script_then_detected(
    script,
    zero,
    recognizer,
    entities,
):
    """The same identifier must be found whichever script writes its digits."""
    pan = to_script("ABCPD1234Z", zero)
    text = f"My PAN is {pan}"

    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert_result(results[0], entities[0], 10, 20, 0.5)


@pytest.mark.parametrize("script, zero", list(NON_INDIC_DIGIT_BLOCKS.items()))
def test_when_digits_are_not_from_an_indic_script_then_not_detected(
    script,
    zero,
    recognizer,
    entities,
):
    """Thai, Arabic-Indic and fullwidth digits are not used for Indian ids."""
    pan = to_script("ABCPD1234Z", zero)
    text = f"My PAN is {pan}"

    assert recognizer.analyze(text, entities) == []


def test_when_token_has_pan_shape_but_not_pan_letters_then_only_weak_score(
    recognizer,
    entities,
):
    """A same-shape token that is not a PAN must not reach a high score."""
    results = recognizer.analyze("My number is ABCD1234EF", entities)

    assert len(results) == 1
    assert results[0].score == 0.01


def test_when_the_same_pan_is_written_in_two_scripts_then_both_match(
    recognizer,
    entities,
):
    """The script of the digits must not move the entity or change its score."""
    ascii_result = recognizer.analyze("My PAN is ABCPD1234Z", entities)[0]
    indic_result = recognizer.analyze(
        "My PAN is " + to_script("ABCPD1234Z", 0x0966), entities
    )[0]

    assert (ascii_result.start, ascii_result.end) == (indic_result.start, indic_result.end)
    assert ascii_result.score == indic_result.score


@pytest.mark.parametrize(
    "pan",
    ["ABCPD1234Z", to_script("ABCPD1234Z", 0x0966)],
    ids=["ascii", "devanagari"],
)
def test_when_context_word_precedes_pan_then_score_is_enhanced(
    pan,
    spacy_nlp_engine,
    recognizer,
    entities,
):
    """Context must raise the score of an Indic PAN exactly as it does an ASCII one."""
    analyzer = AnalyzerEngine(
        registry=RecognizerRegistry(recognizers=[recognizer]),
        nlp_engine=spacy_nlp_engine,
    )

    with_context = analyzer.analyze(f"My PAN is {pan}", language="en")
    without_context = analyzer.analyze(
        f"Reference {pan} was filed.", language="en"
    )

    assert with_context[0].score == pytest.approx(0.85)
    assert without_context[0].score == pytest.approx(0.5)


def test_recognizer_is_registered_in_the_default_yaml():
    """Users reach this recognizer by enabling it in the shipped YAML."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "InPanRecognizer"]

    assert len(entries) == 1, "InPanRecognizer missing from YAML"
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
  - name: InPanRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: in
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    analyzer = AnalyzerEngine(registry=registry)

    results = analyzer.analyze("My PAN is ABCPD1234Z", language="en")

    assert [result.entity_type for result in results] == ["IN_PAN"]
