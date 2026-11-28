from pathlib import Path

import presidio_analyzer
import pytest
import yaml

from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from tests import assert_result
from presidio_analyzer.predefined_recognizers import InPanRecognizer


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
        # 4th character S and N are not assigned holder types
        ("AAASA1111R", 0, (), ()),
        ("ABCPD1234Z", 1, (0, 10), 0.5),
        ("ABCND1234Z", 0, (), ()),
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


@pytest.mark.parametrize(
    "pan, expected",
    [
        # Assigned holder types: the pattern score stands (never promoted)
        ("ABCPD1234Z", None),
        ("abcpd1234z", None),
        ("ABCCD1234Z", None),
        ("ABCTD1234Z", None),
        # PAN shape, unassigned holder type: not a PAN
        ("ABCND1234Z", False),
        ("AAASA1111R", False),
        ("ABC-ND-1234-Z", False),
        # Not the PAN shape: the check does not apply
        ("A1111DFSFS", None),
        ("ABCD1234", None),
    ],
)
def test_validate_result_checks_holder_type(pan, expected, recognizer):
    """Only an exact PAN shape with an unassigned 4th character is rejected."""
    assert recognizer.validate_result(pan) == expected


def test_lookalike_with_unassigned_holder_type_is_not_flagged(recognizer, entities):
    """A PAN-shaped product code with holder type 'X' is not reported."""
    results = recognizer.analyze("SKU ABCXD1234Z in stock", entities)
    assert results == []


def test_loads_from_default_recognizers_yaml_and_detects():
    """Enabled through the shipped YAML entry, the recognizer detects a PAN."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "InPanRecognizer"]
    assert len(entries) == 1, "InPanRecognizer missing from YAML"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entries[0], enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["InPanRecognizer"]

    recognizer = registry.recognizers[0]
    results = recognizer.analyze("PAN ABBPM4567S", ["IN_PAN"])
    assert len(results) == 1
    assert (results[0].start, results[0].end) == (4, 14)
    assert results[0].score == pytest.approx(0.5)
    assert recognizer.analyze("PAN ABBXM4567S", ["IN_PAN"]) == []
