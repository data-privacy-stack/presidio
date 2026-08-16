import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import (
    UsClaimNumberRecognizer,
    UsPrescriptionNumberRecognizer,
    UsPriorAuthorizationNumberRecognizer,
    UsProviderTaxIdRecognizer,
    UsReferralNumberRecognizer,
)

from tests import assert_result
from tests.mocks import ContextAwareNlpEngineMock


def analyze_with_recognizer(text, entity, recognizer, score_threshold=None):
    """Analyze text with one recognizer and its configured score threshold."""
    registry = RecognizerRegistry()
    registry.add_recognizer(recognizer)
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=ContextAwareNlpEngineMock())
    return analyzer.analyze(
        text=text,
        language="en",
        entities=[entity],
        score_threshold=score_threshold,
    )


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_positions",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization PA-987654321 approved for treatment.",
            ((20, 32),),
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
    """Test context enhancement raises matches above the recognizer threshold."""
    results = analyze_with_recognizer(text, entity, recognizer)
    results = sorted(results, key=lambda result: result.start)
    assert len(results) == len(expected_positions)
    for result, (start, end) in zip(results, expected_positions):
        assert_result(result, entity, start, end, 0.7)


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_value, expected_score",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization number: 987654321 approved.",
            "987654321",
            0.7,
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim number: 1234567890123 was paid.",
            "1234567890123",
            0.7,
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim ID 123456789012345 was paid.",
            "123456789012345",
            0.7,
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Rx #1234567",
            "1234567",
            0.6,
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription number: 7654321",
            "7654321",
            0.7,
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "prescription 4455667",
            "4455667",
            0.7,
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Infusion referral number: 2025001234",
            "2025001234",
            0.7,
        ),
        # fmt: on
    ],
)
def test_when_admin_id_follows_label_then_identifier_only_is_detected(
    recognizer, entity, text, expected_value, expected_score
):
    """Test labels enable bare numeric IDs without entering the result span."""
    results = analyze_with_recognizer(text, entity, recognizer)
    start = text.index(expected_value)
    assert len(results) == 1
    assert_result(
        results[0], entity, start, start + len(expected_value), expected_score
    )


def test_when_number_has_different_workflow_label_then_prescription_not_detected():
    """Test a claim label does not support a prescription number match."""
    recognizer = UsPrescriptionNumberRecognizer()
    assert (
        analyze_with_recognizer(
            "The claim 1234567 was paid",
            "US_PRESCRIPTION_NUMBER",
            recognizer,
        )
        == []
    )


@pytest.mark.parametrize(
    "recognizer, entity, text",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "PA-987654321",
        ),
        (UsClaimNumberRecognizer(), "US_CLAIM_NUMBER", "CLM456789123"),
        (UsPrescriptionNumberRecognizer(), "US_PRESCRIPTION_NUMBER", "RX789456123"),
        (UsReferralNumberRecognizer(), "US_REFERRAL_NUMBER", "INF2025001234"),
        (UsProviderTaxIdRecognizer(), "US_PROVIDER_TAX_ID", "12-3456789"),
        # fmt: on
    ],
)
def test_when_us_healthcare_admin_id_lacks_context_then_below_threshold(
    recognizer, entity, text
):
    """Test normal analyzer calls suppress pattern-only matches."""
    assert analyze_with_recognizer(text, entity, recognizer) == []


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
def test_when_us_healthcare_admin_id_has_unrelated_context_then_not_detected(
    recognizer, entity, text
):
    """Test similar-looking workflow IDs stay below the threshold."""
    assert analyze_with_recognizer(text, entity, recognizer) == []


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_score",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "PA-987654321",
            0.1,
        ),
        (UsClaimNumberRecognizer(), "US_CLAIM_NUMBER", "CLM456789123", 0.1),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "RX789456123",
            0.1,
        ),
        (UsReferralNumberRecognizer(), "US_REFERRAL_NUMBER", "INF2025001234", 0.1),
        (UsProviderTaxIdRecognizer(), "US_PROVIDER_TAX_ID", "12-3456789", 0.35),
        # fmt: on
    ],
)
def test_explicit_request_threshold_can_return_pattern_only_matches(
    recognizer, entity, text, expected_score
):
    """Test callers can opt into raw pattern matches for structured analysis."""
    results = analyze_with_recognizer(text, entity, recognizer, score_threshold=0)
    assert len(results) == 1
    assert_result(results[0], entity, 0, len(text), expected_score)


@pytest.mark.parametrize(
    "recognizer, entity, expected_context",
    [
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            ["authorization", "auth", "preauthorization", "approval"],
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            ["claim", "billing"],
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            ["prescription", "pharmacy", "medication"],
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            ["referral", "infusion", "specialty", "referring"],
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            ["provider"],
        ),
    ],
)
def test_us_healthcare_admin_recognizer_metadata(recognizer, entity, expected_context):
    """Test entity metadata, context, and recognizer threshold."""
    assert recognizer.supported_entities == [entity]
    assert recognizer.supported_language == "en"
    assert recognizer.context == expected_context
    assert recognizer.score_thresholds == {entity: 0.6}
