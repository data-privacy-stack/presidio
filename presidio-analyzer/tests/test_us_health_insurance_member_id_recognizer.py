import pytest
from presidio_analyzer.predefined_recognizers import (
    UsHealthInsuranceMemberIdRecognizer,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the US health insurance member ID recognizer."""
    return UsHealthInsuranceMemberIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the US health insurance member ID entity list."""
    return ["US_HEALTH_INSURANCE_MEMBER_ID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        ("Member ID ABC123456789", 1, ((10, 22),)),
        ("member number ZX-987654321 appears on the card", 1, ((14, 26),)),
        ("Subscriber ID HPN12345A9 is active", 1, ((14, 24),)),
        ("Insurance ID BCBSM1234567 was verified", 1, ((13, 25),)),
        ("Health plan ID UHC-12345AB covers the visit", 1, ((15, 26),)),
        ("Plan member ID AET987654 for this policy", 1, ((15, 24),)),
        ("Policy ID CIGNA123456 belongs to the patient", 1, ((10, 21),)),
        ("The insurance card lists subscriber number K123456789", 1, ((43, 53),)),
        # Plausible pattern alone should not be detected.
        ("ABC123456789", 0, ()),
        ("Please store HPN12345A9 in the table", 0, ()),
        # Similar-looking IDs in non-healthcare contexts should not be detected.
        ("Order number ABC123456789 shipped yesterday", 0, ()),
        ("Tracking number ZX-987654321 is in transit", 0, ()),
        ("Case number HPN12345A9 is pending review", 0, ()),
        ("Claim number BCBSM1234567 was denied", 0, ()),
        # Broad generic numeric IDs are intentionally not matched.
        ("Member ID 1234567890", 0, ()),
        # Too short to be a plausible member ID.
        ("Subscriber ID A123", 0, ()),
        # fmt: on
    ],
)
def test_when_us_health_insurance_member_id_in_text_then_detected_only_with_context(
    text, expected_len, expected_positions, recognizer, entities
):
    """Test that plausible member IDs are detected only with insurance context."""
    results = recognizer.analyze(text, entities)
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, 0.3)


def test_us_health_insurance_member_id_recognizer_supported_entity(recognizer):
    """Test that recognizer supports the correct entity."""
    assert recognizer.supported_entities == ["US_HEALTH_INSURANCE_MEMBER_ID"]


def test_us_health_insurance_member_id_recognizer_supported_language(recognizer):
    """Test that recognizer supports English by default."""
    assert recognizer.supported_language == "en"


def test_us_health_insurance_member_id_recognizer_context_words(recognizer):
    """Test that recognizer has appropriate health insurance context words."""
    expected_context = [
        "member id",
        "member number",
        "subscriber id",
        "subscriber number",
        "insurance id",
        "health plan id",
        "plan member id",
        "policy id",
        "policy number",
        "health insurance",
        "insurance member",
        "insurance card",
    ]
    assert recognizer.context == expected_context
