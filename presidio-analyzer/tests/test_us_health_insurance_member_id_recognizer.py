import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import (
    UsHealthInsuranceMemberIdRecognizer,
)

from tests import assert_result
from tests.mocks import ContextAwareNlpEngineMock


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the US health insurance member ID recognizer."""
    return UsHealthInsuranceMemberIdRecognizer()


@pytest.fixture(scope="module")
def entity():
    """Return the US health insurance member ID entity name."""
    return "US_HEALTH_INSURANCE_MEMBER_ID"


def analyze_member_id(text, recognizer, entity, score_threshold=None):
    """Analyze text with the member ID recognizer and its threshold."""
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
    "text, expected_positions",
    [
        # fmt: off
        ("Member ID ABC123456789", ((10, 22),)),
        ("member number ZX-987654321 appears on the card", ((14, 26),)),
        ("Subscriber ID HPN12345A9 is active", ((14, 24),)),
        ("Insurance ID BCBSM1234567 was verified", ((13, 25),)),
        ("Insurance plan ID UHC-12345AB covers the visit", ((18, 29),)),
        ("Plan member ID AET987654 for this policy", ((15, 24),)),
        ("Policy ID CIGNA123456 belongs to the patient", ((10, 21),)),
        ("The insurance card lists subscriber number K123456789", ((43, 53),)),
        # fmt: on
    ],
)
def test_when_member_id_has_context_then_detected(
    text, expected_positions, recognizer, entity
):
    """Test context raises plausible member IDs above the threshold."""
    results = analyze_member_id(text, recognizer, entity)
    results = sorted(results, key=lambda result: result.start)
    assert len(results) == len(expected_positions)
    for result, (start, end) in zip(results, expected_positions):
        assert result.entity_type == entity
        assert result.start == start
        assert result.end == end
        assert result.score == pytest.approx(0.45)


@pytest.mark.parametrize(
    "text",
    [
        "ABC123456789",
        "Please store HPN12345A9 in the table",
        "Order number ABC123456789 shipped yesterday",
        "Tracking number ZX-987654321 is in transit",
        "Case number HPN12345A9 is pending review",
        "Claim number BCBSM1234567 was denied",
        "covid19",
        "sha256",
        "iphone15pro",
        "rfc2119",
        "gpt4turbo",
        "ICD10CM123",
        "ABC-1234567",
    ],
)
def test_when_member_id_lacks_insurance_context_then_below_threshold(
    text, recognizer, entity
):
    """Test pattern-only and unrelated-context values are suppressed."""
    assert analyze_member_id(text, recognizer, entity) == []


@pytest.mark.parametrize(
    "text",
    [
        "Member ID 1234567890",
        "Subscriber ID A123",
    ],
)
def test_when_member_id_pattern_is_implausible_then_not_detected(
    text, recognizer, entity
):
    """Test numeric-only and short values do not match the base pattern."""
    assert (
        analyze_member_id(
            text,
            recognizer,
            entity,
            score_threshold=0,
        )
        == []
    )


def test_explicit_request_threshold_can_return_pattern_only_member_id(
    recognizer, entity
):
    """Test structured callers can opt into the raw pattern match."""
    text = "ABC123456789"
    results = analyze_member_id(
        text,
        recognizer,
        entity,
        score_threshold=0,
    )
    assert len(results) == 1
    assert_result(results[0], entity, 0, len(text), 0.1)


def test_us_health_insurance_member_id_recognizer_metadata(recognizer, entity):
    """Test entity metadata, context, and recognizer threshold."""
    assert recognizer.supported_entities == [entity]
    assert recognizer.supported_language == "en"
    assert recognizer.context == ["member", "subscriber", "insurance", "policy"]
    assert recognizer.patterns[0].name == "Health insurance member ID (weak)"
    assert recognizer.patterns[0].score == 0.1
    assert recognizer.score_thresholds == {entity: 0.4}
