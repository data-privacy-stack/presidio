"""
Tests for DeFuehrerscheinRecognizer (Führerscheinnummer).

Format (FeV Anlage 8, field 5 of the EU card licence): 11 characters,
Behördenschlüssel (Bundesland letter A–P, two digits, one alphanumeric),
five-character base-36 sequential number, check digit (0–9 or X) and issue
number. The check digit is the weighted sum (9 … 1) of the base-36 values of
the first nine characters modulo 11, 10 written as X.

B072RRE2I55 is the number on the official specimen licence. B70752123 with
check digit 9 is the worked example of the Bundesdruckerei guide. All other
numbers are fictitious and carry a correct check digit.
"""
from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.predefined_recognizers import DeFuehrerscheinRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


@pytest.fixture(scope="module")
def recognizer():
    return DeFuehrerscheinRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["DE_FUEHRERSCHEIN"]


@pytest.mark.parametrize(
    "text, expected_spans",
    [
        # fmt: off
        # Official specimen and Bundesdruckerei example
        ("B072RRE2I55", [(0, 11)]),
        ("B7075212391", [(0, 11)]),
        # Check digit X, letters in the sequential number, issue numbers above 9
        ("A01000001X1", [(0, 11)]),
        ("C02ZZZZZZX1", [(0, 11)]),
        ("P61Z0000A51", [(0, 11)]),
        ("M19A2B3C42A", [(0, 11)]),
        # Lowercase: Presidio matches case-insensitively
        ("b072rre2i55", [(0, 11)]),
        # In running text
        ("Führerscheinnummer: B072RRE2I55, Klasse B", [(20, 31)]),
        ("Die Fahrerlaubnis J1234567851 wurde 2019 ausgestellt.", [(18, 29)]),
        # --- Should NOT match ---
        # Wrong check digit (4 instead of 5)
        ("B072RRE2I45", []),
        # Bundesland letter outside A–P
        ("Q072RRE2I55", []),
        # Positions 2–3 must be digits (old fictitious "2 letters + 8 digits" form)
        ("BO12345678A", []),
        # Issue number 0 does not exist
        ("B072RRE2I50", []),
        # Too short and too long
        ("B072RRE2I5", []),
        ("B072RRE2I551", []),
        # fmt: on
    ],
)
def test_when_de_fuehrerschein_numbers_then_exact_spans_and_score(
    text, expected_spans, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert [(result.start, result.end) for result in results] == expected_spans
    assert all(result.score == 0.4 for result in results)


def test_when_context_word_then_score_increases(recognizer, entities):
    text = "Nummer B072RRE2I55"
    results = recognizer.analyze(text, entities)
    enhanced = LemmaContextAwareEnhancer().enhance_using_context(
        text,
        results,
        NlpArtifacts([], [], [], [], None, "de"),
        [recognizer],
        ["führerschein"],
    )
    assert results[0].score == 0.4
    assert enhanced[0].score > results[0].score


def test_loads_from_default_recognizers_yaml():
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "DeFuehrerscheinRecognizer"]
    assert len(entries) == 1
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["de"],
            "recognizers": [dict(entries[0], enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["DeFuehrerscheinRecognizer"]
    results = registry.recognizers[0].analyze("B072RRE2I55", ["DE_FUEHRERSCHEIN"])
    assert [(result.start, result.end) for result in results] == [(0, 11)]
