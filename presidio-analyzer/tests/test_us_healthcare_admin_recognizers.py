import pytest
from presidio_analyzer.predefined_recognizers import (
    UsClaimNumberRecognizer,
    UsPrescriptionNumberRecognizer,
    UsPriorAuthorizationNumberRecognizer,
    UsProviderTaxIdRecognizer,
    UsReferralNumberRecognizer,
)

from tests import assert_result


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_positions",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior Authorization Number PA-987654321 approved for treatment.",
            ((27, 39),),
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Processed healthcare claim CLM456789123 was paid.",
            ((27, 39),),
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription number RX789456123 was filled by the pharmacy.",
            ((20, 31),),
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Infusion referral number INF2025001234 is ready for scheduling.",
            ((25, 38),),
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "Provider Tax ID 12-3456789 belongs to the billing provider.",
            ((16, 26),),
        ),
        # fmt: on
    ],
)
def test_when_us_healthcare_admin_id_has_context_then_detected(
    recognizer, entity, text, expected_positions
):
    """Test that healthcare administrative identifiers are found with context."""
    results = recognizer.analyze(text, [entity])
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == len(expected_positions)
    for result, (start, end) in zip(results, expected_positions):
        assert_result(result, entity, start, end, 0.35)


@pytest.mark.parametrize(
    "recognizer, entity, text",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "PA-987654321",
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "CLM456789123",
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "RX789456123",
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "INF2025001234",
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "12-3456789",
        ),
        # fmt: on
    ],
)
def test_when_us_healthcare_admin_id_lacks_context_then_not_detected(
    recognizer, entity, text
):
    """Test that plausible patterns alone are not detected."""
    assert recognizer.analyze(text, [entity]) == []


@pytest.mark.parametrize(
    "recognizer, entity, text",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Order number PA-987654321 is ready.",
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Tracking number CLM456789123 is active.",
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Case number RX789456123 is pending.",
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Claim number INF2025001234 was denied.",
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "Invoice number 12-3456789 was posted.",
        ),
        # fmt: on
    ],
)
def test_when_us_healthcare_admin_id_has_negative_context_then_not_detected(
    recognizer, entity, text
):
    """Test that similar-looking non-healthcare workflow IDs are not detected."""
    assert recognizer.analyze(text, [entity]) == []


@pytest.mark.parametrize(
    "recognizer, entity, expected_context",
    [
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            [
                "prior authorization",
                "prior auth",
                "preauthorization",
                "pre-auth",
                "authorization number",
                "auth number",
                "approval request",
                "treatment authorization",
                "drug authorization",
            ],
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            [
                "claim number",
                "claim id",
                "claim",
                "healthcare claim",
                "medical claim",
                "billing",
                "billing claim",
                "claims processing",
                "processed claim",
            ],
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            [
                "prescription number",
                "prescription id",
                "rx number",
                "rx no",
                "pharmacy",
                "prescription",
                "medication order",
                "drug order",
            ],
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            [
                "referral number",
                "referral id",
                "referral",
                "infusion referral",
                "infusion therapy",
                "specialty referral",
                "specialty care",
                "referring provider",
            ],
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            [
                "provider tax id",
                "provider tin",
                "provider ein",
                "tax id",
                "tin",
                "ein",
                "healthcare organization",
                "provider organization",
                "billing provider",
                "rendering provider",
            ],
        ),
    ],
)
def test_us_healthcare_admin_recognizer_metadata(
    recognizer, entity, expected_context
):
    """Test supported entities, language, and context words."""
    assert recognizer.supported_entities == [entity]
    assert recognizer.supported_language == "en"
    assert recognizer.context == expected_context
