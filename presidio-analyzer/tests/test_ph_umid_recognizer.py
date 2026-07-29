"""Tests for Philippine UMID (PH_UMID) recognizer."""

import pytest
from presidio_analyzer.predefined_recognizers import PhUmidRecognizer

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of PhUmidRecognizer."""
    return PhUmidRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the supported entities for PhUmidRecognizer."""
    return ["PH_UMID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # VALID
        ("0111-1234567-8", 1, ((0, 14),), ((0.4, 1.0),)),
        ("0000-0000000-0", 1, ((0, 14),), ((0.4, 1.0),)),
        ("001112345678", 1, ((0, 12),), ((0.2, 1.0),)),
        ("My UMID number is 0111-1234567-8", 1, ((18, 32),), ((0.4, 1.0),)),
        ("UMID: 001112345678", 1, ((6, 18),), ((0.2, 1.0),)),
        ("CRN: 0111-1234567-8", 1, ((5, 19),), ((0.4, 1.0),)),
        ("philhealth 001112345678", 1, ((11, 23),), ((0.2, 1.0),)),
        ("gsis 0111-1234567-8", 1, ((5, 19),), ((0.4, 1.0),)),
        ("sss: 0111-1234567-8", 1, ((5, 19),), ((0.4, 1.0),)),
        ("pag-ibig 0111-1234567-8", 1, ((9, 23),), ((0.4, 1.0),)),
        ("umid card 0111-1234567-8", 1, ((10, 24),), ((0.4, 1.0),)),
        ("unified multi-purpose id 0111-1234567-8", 1, ((25, 39),), ((0.4, 1.0),)),
        ("unified multipurpose id 0111-1234567-8", 1, ((24, 38),), ((0.4, 1.0),)),
        ("common reference number 0111-1234567-8", 1, ((24, 38),), ((0.4, 1.0),)),
        ("1234-1234567-8", 1, ((0, 14),), ((0.4, 1.0),)),
        ("9999-9999999-9", 1, ((0, 14),), ((0.4, 1.0),)),
        # INVALID
        ("123456789012", 1, ((0, 12),), ((0.2, 1.0),)),
        ("987654321098", 1, ((0, 12),), ((0.2, 1.0),)),
        ("12345", 0, (), ()),
        ("1234567890123", 0, (), ()),
        ("hello world", 0, (), ()),
        ("0111-123456-8", 0, (), ()),
        ("0111-12345678-8", 0, (), ()),
        ("011-1234567-8", 0, (), ()),
        ("01111-1234567-8", 0, (), ()),
        ("0111-1234567-89", 0, (), ()),
        ("0111-1234567-", 0, (), ()),
        ("-1234567-8", 0, (), ()),
        ("0111 1234567 8", 0, (), ()),
        ("0111.1234567.8", 0, (), ()),
        # MULTIPLE
        (
            "First: 0111-1234567-8, Second: 001112345678",
            2,
            ((7, 21), (31, 43)),
            ((0.4, 1.0), (0.2, 1.0)),
        ),
        (
            "0000-0000000-0 and 1111-1111111-1",
            2,
            ((0, 14), (19, 33)),
            ((0.4, 1.0), (0.4, 1.0)),
        ),
    ],
)
def test_when_umid_in_text_then_all_umids_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    """Test that PH UMID recognizer correctly identifies numbers."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["PH_UMID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"
