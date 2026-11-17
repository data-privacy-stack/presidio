from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer.predefined_recognizers import EsNssRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return EsNssRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ES_NSS"]


@pytest.mark.parametrize(
    "text, expected_positions",
    [
        # fmt: off
        # 2812345678 mod 97 = 40
        ("28/12345678/40", ((0, 14),)),
        ("28 12345678 40", ((0, 14),)),
        ("28-12345678-40", ((0, 14),)),
        ("281234567840", ((0, 12),)),
        ("Número de afiliación: 46/87654321/20 en alta", ((22, 36),)),
        # older seven-digit sequence: 28 * 10^7 + 1234567 mod 97 = 42
        ("28/1234567/42", ((0, 13),)),
        # the same number zero-padded keeps its control digits
        ("28/01234567/42", ((0, 14),)),
        ("08/07654321/77", ((0, 14),)),
        # fmt: on
    ],
)
def test_when_valid_nss_then_detected(
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
        "28/12345678/41",    # wrong control digits
        "28/01234567/85",    # zero-padded sequence read as plain concatenation
        "28/12345678 40",    # mixed separators
        "123456789012",      # 12-digit order number: 1234567890 mod 97 = 2
        "00/00000000/00",    # all-zero placeholder passes the check
        "2812345678400",     # 13 digits
        # fmt: on
    ],
)
def test_when_invalid_nss_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


def test_nss_loads_and_detects_when_enabled_in_yaml(entities, max_score):
    """The shipped YAML entry builds a working recognizer once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == "EsNssRecognizer")
    assert entry["enabled"] is False
    assert entry["country_code"] == "es"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["es"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["EsNssRecognizer"]
    results = registry.recognizers[0].analyze("NSS 28/12345678/40", entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 4, 18, max_score)
