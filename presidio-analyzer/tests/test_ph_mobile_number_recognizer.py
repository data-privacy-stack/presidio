"""Tests for Philippine mobile number (PH_MOBILE_NUMBER) recognizer."""

import pytest
from presidio_analyzer.predefined_recognizers import PhoneRecognizer

from tests import assert_result_within_score_range

PH_CONTEXT = [
    "mobile",
    "phone",
    "cell",
    "cellphone",
    "telepono",
    "numero",
    "mobile number",
    "contact number",
    "numero ng telepono",
    "contact",
    "number",
    "call",
    "tawag",
    "mensahe",
    "sms",
    "whatsapp",
    "viber",
    "telegram",
    "signal",
    "celphone",
    "phone number",
    "mobile no",
]


@pytest.fixture(scope="module")
def recognizer():
    """Create a PH-configured PhoneRecognizer instance for testing."""
    return PhoneRecognizer(
        supported_regions=["PH"],
        supported_entity="PH_MOBILE_NUMBER",
        context=PH_CONTEXT,
        supported_language="en",
    )


@pytest.fixture(scope="module")
def entities():
    """Return the PH_MOBILE_NUMBER entity type for testing."""
    return ["PH_MOBILE_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # International format (+63)
        ("+63 917 123 4567", 1, ((0, 16),), ((0.4, 1.0),)),
        ("+639171234567", 1, ((0, 13),), ((0.4, 1.0),)),
        ("+63-917-123-4567", 1, ((0, 16),), ((0.4, 1.0),)),
        ("+63 (917) 123 4567", 1, ((0, 18),), ((0.4, 1.0),)),
        # National format (0)
        ("09171234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("0917 123 4567", 1, ((0, 13),), ((0.3, 1.0),)),
        ("0917-123-4567", 1, ((0, 13),), ((0.3, 1.0),)),
        ("0 (917) 123 4567", 1, ((0, 16),), ((0.3, 1.0),)),
        # Local format (bare number without prefix) - not reliably detected
        # by phonenumbers for PH region
        ("9171234567", 0, (), ()),
        ("917 123 4567", 0, (), ()),
        ("917-123-4567", 0, (), ()),
        # Valid PH mobile prefixes
        ("09171234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09181234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09191234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09201234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09211234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09271234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09281234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09291234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09301234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09391234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09471234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09491234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09561234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09611234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09661234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09671234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09771234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09941234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09951234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09961234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09971234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09981234567", 1, ((0, 11),), ((0.3, 1.0),)),
        ("09991234567", 1, ((0, 11),), ((0.3, 1.0),)),
        # In sentence with context
        (
            "My mobile number is +639171234567.",
            1,
            ((20, 33),),
            ((0.4, 1.0),),
        ),
        (
            "Telepono: 09171234567",
            1,
            ((10, 21),),
            ((0.3, 1.0),),
        ),
        (
            "Numero: 9171234567",
            0,
            (),
            (),
        ),
        # Multiple numbers
        (
            "First: +639171234567, Second: 09181234567",
            2,
            ((7, 20), (30, 41)),
            ((0.4, 1.0), (0.3, 1.0)),
        ),
        # Invalid numbers (not mobile, or geographical/landline)
        # Random 11-digit number
        ("12345678901", 0, (), ()),
        # Invalid: too short
        ("0917123456", 0, (), ()),
        # Invalid: too long (12 digits)
        ("091712345678", 0, (), ()),
        # False positive: embedded in longer number
        ("15091712345678", 0, (), ()),
        # Not a phone number
        ("hello world", 0, (), ()),
    ],
)
def test_when_phone_in_text_then_all_phones_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    """Test that PH mobile number recognizer correctly identifies numbers."""
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
    assert recognizer.supported_entities == ["PH_MOBILE_NUMBER"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"
