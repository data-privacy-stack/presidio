from pathlib import Path

import presidio_analyzer
import pytest
import yaml

from tests import assert_result
from presidio_analyzer.predefined_recognizers import EsNifRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


@pytest.fixture(scope="module")
def recognizer():
    return EsNifRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ES_NIF"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # valid NIF scores
        ("55555555K", 1, ((0, 9),),),
        ("55555555-K", 1, ((0, 10),),),
        ("1111111-G", 1, ((0, 9),),),
        ("1111111G", 1, ((0, 8),),),
        ("01111111G", 1, ((0, 9),),),
        # valid NIF in lowercase (control letter is upper-cased before checksum)
        ("55555555k", 1, ((0, 9),),),
        ("12345678z", 1, ((0, 9),),),
        # uppercase still detected
        ("12345678Z", 1, ((0, 9),),),
        # invalid NIF scores
        ("401-023-2138", 0, ()),
        # invalid checksum stays rejected regardless of case
        ("12345678a", 0, ()),
        # dots as thousands separators, with or without a hyphen
        ("12.345.678-Z", 1, ((0, 12),),),
        ("12.345.678Z", 1, ((0, 11),),),
        ("1.234.567-L", 1, ((0, 11),),),
        ("Mi DNI es 12.345.678-Z y vivo en Madrid", 1, ((10, 22),),),
        # separators do not bypass the checksum
        ("12.345.678-A", 0, ()),
        # dots are all or nothing
        ("12.345678Z", 0, ()),
        # a space before the control letter is not accepted: in all-caps text
        # an amount followed by a one-letter word would pass the checksum
        # (87654321 maps to X) one time in 23
        ("12345678 Z", 0, ()),
        ("PAGÓ 87654321 X 2 UNIDADES", 0, ()),
        # the digits of an NIE written with separators are not a NIF
        ("X-1234567-L", 0, ()),
        ("x-1234567-l", 0, ()),
        ("X 1234567L", 0, ()),
        # the conjunction y before a 7-digit NIF is not an NIE prefix
        ("DNI 12345678Z y 1111111G", 2, ((4, 13), (16, 24),),),
        # an 8-digit NIF after a standalone X- is still a NIF
        ("X-12345678Z", 1, ((2, 11),),),
        # fmt: on
    ],
)
def test_when_all_es_nifes_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


def test_nif_loads_and_detects_when_enabled_in_yaml(entities, max_score):
    """The shipped YAML entry builds a recognizer that detects separated NIFs."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == "EsNifRecognizer")

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["es"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["EsNifRecognizer"]
    results = registry.recognizers[0].analyze("DNI 12.345.678-Z", entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 4, 16, max_score)
