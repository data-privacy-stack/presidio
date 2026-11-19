from pathlib import Path

import pytest
import yaml
from presidio_analyzer.predefined_recognizers import FrRibRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Return a FrRibRecognizer."""
    return FrRibRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entities under test."""
    return ["FR_RIB"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # Valid RIBs: the key equals 97 - (89*bank + 15*branch + 3*account) mod 97.
        # The first two are the examples used on the French Wikipedia RIB page
        # and in public IBAN documentation (FR14 2004 1010 0505 0001 3M02 606).
        ("30006000011234567890189", 1, ((0, 23),)),
        ("30006 00001 12345678901 89", 1, ((0, 26),)),
        # Account number with a letter (A-I, J-R and S-Z map to different digits)
        ("20041010050500013M02606", 1, ((0, 23),)),
        ("20041 01005 0500013M026 06", 1, ((0, 26),)),
        ("20041010050500013m02606", 1, ((0, 23),)),
        # Embedded in text
        ("Mon RIB : 30006 00001 12345678901 89.", 1, ((10, 36),)),
        ("RIB 30006000011234567890189, merci", 1, ((4, 27),)),
        # Two numbers in the same text
        ("30006000011234567890189 and 20041010050500013M02606", 2, ((0, 23), (28, 51))),
        # Invalid: wrong key
        ("30006000011234567890188", 0, ()),
        ("20041 01005 0500013M026 07", 0, ()),
        # Invalid: right shape, wrong length
        ("3000600001123456789018", 0, ()),
        ("300060000112345678901890", 0, ()),
        # Invalid: a longer digit string must not match in part
        ("130006000011234567890189", 0, ()),
        # Invalid: other separators are not a RIB format
        ("30006-00001-12345678901-89", 0, ()),
        # A French IBAN is grouped differently and belongs to IBAN_CODE
        ("FR7630006000011234567890189", 0, ()),
        ("FR76 3000 6000 0112 3456 7890 189", 0, ()),
        # Similar numbers that are not a RIB
        ("Call 0612345678 or 0145678901", 0, ()),
        ("4111 1111 1111 1111", 0, ()),
        # fmt: on
    ],
)
def test_when_all_fr_ribs_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    """Valid RIBs are found with the maximum score, invalid ones are ignored."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "rib, expected",
    [
        ("30006000011234567890189", True),
        ("30006 00001 12345678901 89", True),
        ("20041010050500013M02606", True),
        # Wrong key, length or characters
        ("30006000011234567890188", False),
        ("3000600001123456789018", False),
        ("3000600001123456789018A", False),
        ("A0006000011234567890189", False),
        ("30006000011234567890-89", False),
    ],
)
def test_validate_result_checksum(rib, expected, recognizer):
    """validate_result accepts only a correct 23 character RIB."""
    assert recognizer.validate_result(rib) is expected


def test_context_words_are_set(recognizer):
    """The recognizer exposes context words, language and entity."""
    assert "rib" in recognizer.context
    assert recognizer.supported_language == "fr"
    assert recognizer.supported_entities == ["FR_RIB"]


def _default_conf():
    """Load default_recognizers.yaml."""
    conf_path = (
        Path(__file__).parent.parent
        / "presidio_analyzer"
        / "conf"
        / "default_recognizers.yaml"
    )
    return yaml.safe_load(conf_path.read_text())


def test_when_default_yaml_then_fr_rib_is_disabled(tmp_path):
    """Country specific recognizers ship disabled."""
    conf = _default_conf()
    conf["supported_languages"] = ["en", "fr"]
    conf_file = tmp_path / "default.yaml"
    conf_file.write_text(yaml.safe_dump(conf))

    registry = RecognizerRegistryProvider(
        conf_file=str(conf_file)
    ).create_recognizer_registry()

    names = {type(r).__name__ for r in registry.recognizers}
    assert "FrRibRecognizer" not in names


def test_when_enabled_in_yaml_then_fr_rib_loads_for_fr_and_en(tmp_path):
    """Enabling the entry loads one recognizer per language."""
    conf = _default_conf()
    conf["supported_languages"] = ["en", "fr"]
    for recognizer_conf in conf["recognizers"]:
        if recognizer_conf["name"] == "FrRibRecognizer":
            recognizer_conf["enabled"] = True
    conf_file = tmp_path / "enabled.yaml"
    conf_file.write_text(yaml.safe_dump(conf))

    registry = RecognizerRegistryProvider(
        conf_file=str(conf_file)
    ).create_recognizer_registry()

    loaded = [r for r in registry.recognizers if type(r).__name__ == "FrRibRecognizer"]
    assert {r.supported_language for r in loaded} == {"en", "fr"}
    assert all(r.supported_entities == ["FR_RIB"] for r in loaded)
