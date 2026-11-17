from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer.predefined_recognizers import EsCccRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return EsCccRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ES_CCC"]


@pytest.mark.parametrize(
    "text, expected_positions",
    [
        # fmt: off
        # worked example from the AEB specification
        ("0012 0345 03 0000067890", ((0, 23),)),
        ("2100 0418 45 0200051332", ((0, 23),)),
        ("2100-0418-45-0200051332", ((0, 23),)),
        ("21000418450200051332", ((0, 20),)),
        ("Domiciliación en la cuenta 2100 0418 45 0200051332.", ((27, 50),)),
        # fmt: on
    ],
)
def test_when_valid_ccc_then_detected(
    text, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == len(expected_positions)
    for result, (start, end) in zip(results, expected_positions):
        assert_result(result, entities[0], start, end, max_score)


@pytest.mark.parametrize(
    "text",
    [
        # fmt: off
        "2100 0418 46 0200051332",          # wrong control digits
        "2100 0418-45 0200051332",          # mixed separators
        "12345678901234567890",             # 20-digit tracking number
        "0000 0000 00 0000000000",          # all-zero placeholder passes the check
        "ES9121000418450200051332",         # an IBAN, left to IbanRecognizer
        "ES91 2100 0418 4502 0005 1332",    # a grouped IBAN
        # fmt: on
    ],
)
def test_when_invalid_ccc_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


def test_ccc_loads_and_detects_when_enabled_in_yaml(entities, max_score):
    """The shipped YAML entry builds a working recognizer once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == "EsCccRecognizer")
    assert entry["enabled"] is False
    assert entry["country_code"] == "es"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["es"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["EsCccRecognizer"]
    results = registry.recognizers[0].analyze("CCC 2100 0418 45 0200051332", entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 4, 27, max_score)
