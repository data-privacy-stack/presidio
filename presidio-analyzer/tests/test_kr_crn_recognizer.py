import copy
import tempfile
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer.predefined_recognizers.country_specific.korea.kr_crn_recognizer import (
    KrCrnRecognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return KrCrnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["KR_CRN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid CRNs (check digit matches -> validated, max score) ---
        # Stock company (corporate type code 11)
        (
            "110111-1234569",
            1,
            ((0, 14),),
            ((1.0, 1.0),),
        ),
        # Without hyphen
        (
            "1101111234569",
            1,
            ((0, 13),),
            ((1.0, 1.0),),
        ),
        # Incorporated foundation (corporate type code 22)
        (
            "134322-0000114",
            1,
            ((0, 14),),
            ((1.0, 1.0),),
        ),
        # Foreign stock company (corporate type code 81)
        (
            "110181-0001235",
            1,
            ((0, 14),),
            ((1.0, 1.0),),
        ),
        # Inside a Korean sentence
        (
            "법인등록번호 110111-1234569",
            1,
            ((7, 21),),
            ((1.0, 1.0),),
        ),
        # Format matches but check digit does not (score stays at pattern
        # score: CRNs issued on or after 2025-01-31 carry no check digit) ---
        (
            "110111-1234560",
            1,
            ((0, 14),),
            ((0.5, 0.5),),
        ),
        # Invalid corporate type code (positions 5-6) -> no match ---
        # 16 is not an assigned corporate type code
        (
            "110116-1234567",
            0,
            (),
            (),
        ),
        # 00 is not an assigned corporate type code
        (
            "110100-1234567",
            0,
            (),
            (),
        ),
        # 61 is not an assigned corporate type code
        (
            "110161-1234567",
            0,
            (),
            (),
        ),
        # Invalid format -> no match ---
        # Too short
        (
            "110111-123456",
            0,
            (),
            (),
        ),
        # Too long
        (
            "110111-12345678",
            0,
            (),
            (),
        ),
        # Contains letters
        (
            "110111-123456A",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_all_crns_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_checksum_validation():
    """Check digit = (10 - (alternating 1,2 weighted sum mod 10)) mod 10."""
    assert KrCrnRecognizer._validate_checksum("1101111234569")
    assert not KrCrnRecognizer._validate_checksum("1101111234560")


def test_failed_checksum_returns_none_not_false(recognizer):
    """A failed checksum must not invalidate the result.

    CRNs issued on or after January 31, 2025 (Supreme Court Rule No. 3173)
    have a 7-digit serial number and no check digit, so a mismatch does not
    prove the number invalid.
    """
    assert recognizer.validate_result("110111-1234569") is True
    assert recognizer.validate_result("110111-1234560") is None


def test_default_supported_language_is_ko():
    """Default language must be ``ko``, like the other Korean recognizers."""
    assert KrCrnRecognizer().supported_language == "ko"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes."""
    recognizer = KrCrnRecognizer(name="CustomKrCrn")
    assert recognizer.name == "CustomKrCrn"


@pytest.mark.parametrize("language", ["ko", "kr"])
def test_loads_from_default_recognizers_yaml(language):
    """Recognizer is registered in the default YAML and loads once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "KrCrnRecognizer"]
    assert len(entries) == 1, "KrCrnRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "kr"
    assert language in entry["supported_languages"]

    entry = copy.deepcopy(entry)
    entry["enabled"] = True
    tmp = Path(tempfile.mkdtemp()) / "conf.yaml"
    tmp.write_text(
        yaml.safe_dump({"supported_languages": [language], "recognizers": [entry]})
    )
    provider = RecognizerRegistryProvider(conf_file=str(tmp))
    registry = provider.create_recognizer_registry()
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "KR_CRN" in entities
