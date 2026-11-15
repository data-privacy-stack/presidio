from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import EntityRecognizer
from presidio_analyzer.predefined_recognizers import (
    CardTrackDataRecognizer,
    CreditCardRecognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

# Test card numbers only (Luhn valid, issued for testing by the card brands).
# Layouts: ISO/IEC 7813. Track 1 is %B PAN ^ NAME ^ YYMM SSS discretionary ?
# and track 2 is ; PAN = YYMM SSS discretionary ?

TRACK1 = "%B4111111111111111^DOE/JOHN^29121010000000000000?"
TRACK2 = ";4111111111111111=29121010000000000000?"


@pytest.fixture(scope="module")
def recognizer():
    """Shared recognizer instance."""
    return CardTrackDataRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Entity list passed to analyze."""
    return ["CARD_TRACK_DATA"]


@pytest.mark.parametrize(
    "text, expected_spans",
    [
        # fmt: off
        # Full tracks with sentinels
        (TRACK1, [(0, 49)]),
        (TRACK2, [(0, 39)]),
        # Both tracks as one reader output
        (TRACK1 + TRACK2, [(0, 49), (49, 88)]),
        # Sentinels stripped by a reader or log formatter
        ("B4111111111111111^DOE/JOHN^2912101", [(0, 34)]),
        ("4111111111111111=2912101", [(0, 24)]),
        # Embedded in surrounding text
        ("swipe log: " + TRACK1 + " end", [(11, 60)]),
        ("raw=" + TRACK2 + ", status=ok", [(4, 43)]),
        # Other brands and name formats
        ("%B5555555555554444^SMITH/JANE MS^3001201?", [(0, 41)]),
        (";4012888888881881=27062010000?", [(0, 30)]),
        # Letters in track 1 discretionary data run to the end sentinel
        ("%B4111111111111111^DOE/JOHN^2912101ABC000123? next", [(0, 45)]),
        # Lowercase format code, as some readers emit it
        ("%b4111111111111111^DOE/JOHN^2912101?", [(0, 36)]),
        # Without sentinels, trailing words before a question mark stay out
        ("is B4111111111111111^DOE/JOHN^2912101 valid?", [(3, 37)]),
        # Without sentinels, letters in discretionary data are still covered
        ("log %B4111111111111111^DOE/JOHN^2912101ABC000123 x", [(4, 48)]),
        # Punctuation in track 1 discretionary data runs to the end sentinel
        ("%B4111111111111111^DOE/JOHN^2912101000-00/0? x", [(0, 44)]),
        # Without sentinels, trailing numbers after a space stay out
        ("B4111111111111111^DOE/JOHN^2912101 200 OK", [(0, 34)]),
        # fmt: on
    ],
)
def test_when_track_data_then_detected_with_max_score(
    text, expected_spans, recognizer, entities
):
    """Valid tracks are found with exact spans and promoted by validation."""
    results = sorted(recognizer.analyze(text, entities), key=lambda r: r.start)
    assert [(r.start, r.end) for r in results] == expected_spans
    for result in results:
        assert result.entity_type == "CARD_TRACK_DATA"
        assert result.score == pytest.approx(EntityRecognizer.MAX_SCORE)


@pytest.mark.parametrize(
    "text",
    [
        # fmt: off
        # Luhn fails
        "%B4111111111111112^DOE/JOHN^29121010000000000000?",
        ";4111111111111112=29121010000000000000?",
        # Lowercase format code still has to pass Luhn
        "%b4111111111111112^DOE/JOHN^2912101?",
        # Service code first digit not assigned by ISO/IEC 7813 (0, 3, 4, 8)
        "%B4111111111111111^DOE/JOHN^29120010000000000000?",
        ";4111111111111111=29123010000000000000?",
        # Random digits=digits that pass Luhn and the month check only
        "{1234567890123452=1203456789}",
        # Expiry month out of range
        "%B4111111111111111^DOE/JOHN^29131010000000000000?",
        ";4111111111111111=29001010000000000000?",
        # Lookalikes: query strings and ids with an equals sign
        "order_id=4111111111111111&exp=2912",
        "ref 1234567890123=4567890",
        "user=4111111111111111",
        # Card number alone is CREDIT_CARD, not track data
        "4111111111111111",
        # Too short to be a PAN
        ";41111111111=2912101?",
        # fmt: on
    ],
)
def test_when_not_track_data_then_not_detected(text, recognizer, entities):
    """Failed checks and lookalike strings are not flagged."""
    assert recognizer.analyze(text, entities) == []


def test_track2_span_contains_the_credit_card_span(recognizer, entities):
    """Documents the overlap with CREDIT_CARD on track 2.

    CreditCardRecognizer flags the PAN inside track 2. This recognizer flags
    the whole track around it, so the anonymizer masks expiry, service code
    and discretionary data too, not only the PAN.
    """
    card = CreditCardRecognizer().analyze(TRACK2, ["CREDIT_CARD"])
    track = recognizer.analyze(TRACK2, entities)
    assert [(r.start, r.end) for r in card] == [(1, 17)]
    assert [(r.start, r.end) for r in track] == [(0, 39)]


def test_validate_result_returns_none_when_fields_unreadable(recognizer):
    """A custom pattern that does not carry track fields leaves the score alone."""
    assert recognizer.validate_result("no track fields here") is None


def test_track1_pan_is_missed_by_credit_card_recognizer():
    """Documents the gap this recognizer closes.

    The format code ``B`` sits directly before the PAN in track 1, so the
    word boundary that ``CreditCardRecognizer`` anchors on is absent.
    """
    assert CreditCardRecognizer().analyze(TRACK1, ["CREDIT_CARD"]) == []


def test_loads_from_default_recognizers_yaml_and_detects(entities):
    """Detection must work through the path users configure."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    matching = [r for r in recognizers if r.get("name") == "CardTrackDataRecognizer"]
    assert len(matching) == 1, "CardTrackDataRecognizer missing from YAML"
    entry = matching[0]
    assert "country_code" not in entry

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "CardTrackDataRecognizer"
    ]
    results = registry.recognizers[0].analyze(TRACK2, entities)
    assert [(r.start, r.end) for r in results] == [(0, 39)]
    assert results[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)


def test_name_kwarg_is_accepted():
    """The YAML loader passes ``name``; the constructor must take it."""
    assert CardTrackDataRecognizer(name="CustomTrack").name == "CustomTrack"
