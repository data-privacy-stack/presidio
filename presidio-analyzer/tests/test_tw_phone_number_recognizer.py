"""Tests for Taiwan phone number (TW_PHONE_NUMBER) recognizer."""

import pytest
from presidio_analyzer.predefined_recognizers import TwPhoneNumberRecognizer

from tests import assert_result_within_score_range

TAIWAN_CONTEXT = [
    "電話",
    "電話號碼",
    "手機",
    "手機號碼",
    "行動電話",
    "聯絡電話",
    "市話",
    "office phone",
    "phone",
    "phone number",
    "mobile",
    "cell",
    "call",
    "contact",
]


@pytest.fixture(scope="module")
def recognizer():
    """Create a TW-configured PhoneRecognizer instance for testing."""
    return TwPhoneNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the TW_PHONE_NUMBER entity type for testing."""
    return ["TW_PHONE_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        ("+886912345678", 1, ((0, 13),), ((0.4, 1.0),)),
        ("+886 912 345 678", 1, ((0, 16),), ((0.4, 1.0),)),
        ("0912345678", 1, ((0, 10),), ((0.4, 1.0),)),
        ("02 2345 6789", 1, ((0, 12),), ((0.4, 1.0),)),
        ("(02) 2345-6789", 1, ((0, 14),), ((0.4, 1.0),)),
        (
            "電話：02 2345 6789",
            1,
            ((3, 15),),
            ((0.4, 1.0),),
        ),
        (
            "手機號碼 0912345678 可於上班時間聯絡。",
            1,
            ((5, 15),),
            ((0.4, 1.0),),
        ),
        (
            "Office phone +886 2 2345 6789, mobile 0912345678",
            2,
            ((13, 29), (38, 48),),
            ((0.4, 1.0), (0.4, 1.0),),
        ),
        ("1234567890", 0, (), ()),
        ("10000000146", 0, (), ()),
        ("091234567", 0, (), ()),
        ("09123456789", 0, (), ()),
        ("hello world", 0, (), ()),
    ],
)
def test_when_tw_phone_number_in_text_then_all_matches_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    """Test that Taiwan phone number recognizer correctly identifies numbers."""
    results = sorted(
        recognizer.analyze(text, entities),
        key=lambda result: result.start,
    )
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["TW_PHONE_NUMBER"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "zh"


def test_context_words(recognizer):
    """Test that context words are properly set."""
    assert recognizer.context == TAIWAN_CONTEXT
