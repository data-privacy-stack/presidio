from pathlib import Path

import presidio_analyzer
import pytest
import yaml

from presidio_analyzer import EntityRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from tests import assert_result
from presidio_analyzer.predefined_recognizers.country_specific.india.in_gstin_recognizer import InGstinRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return InGstinRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_GSTIN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # Valid GSTINs with high confidence
        ("27ABCDE1234F1Z0", 1, (0, 15), 1.0),
        ("07PQRST6789K1ZY", 1, (0, 15), 1.0),
        ("01ABCDE1234F1ZE", 1, (0, 15), 1.0),
        ("37ABCDE1234F1ZZ", 1, (0, 15), 1.0),
        
        # Valid GSTINs with medium confidence (different PAN format)
        ("27ABCDE1234F1Z0", 1, (0, 15), 1.0),
        ("07PQRST6789K1ZY", 1, (0, 15), 1.0),
        
        # Valid GSTINs with low confidence (generic pattern)
        ("27ABCDE1234F1Z0", 1, (0, 15), 1.0),
        
        # GSTIN with context
        ("My GSTIN number is 27ABCDE1234F1Z0 for business registration", 1, (19, 34), 1.0),
        ("GST registration: 07PQRST6789K1ZY", 1, (18, 33), 1.0),
        ("Tax identification GSTIN: 01ABCDE1234F1ZE", 1, (26, 41), 1.0),
        
        # Multiple GSTINs
        ("GSTINs: 27ABCDE1234F1Z0 and 07PQRST6789K1ZY", 2, (8, 23), 1.0),
        
        # Invalid GSTINs (should not be detected)
        ("27ABCDE1234F1Z", 0, (), ()),  # Too short
        ("27ABCDE1234F1Z05", 0, (), ()),  # Too long
        ("00ABCDE1234F1ZG", 0, (), ()),  # Invalid state code
        ("38ABCDE1234F1ZX", 0, (), ()),  # Invalid state code
        ("27ABCDE1234F1Y2", 0, (), ()),  # Missing 'Z' at position 14
        ("27ABCDE1234F1Z", 0, (), ()),  # Missing checksum
    ],
)
def test_when_gstin_in_text_then_all_gstins_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    
    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )


@pytest.mark.parametrize(
    "text, expected_len",
    [
        # Invalid formats
        ("", 0),
        ("123456789012345", 0),  # All digits
        ("ABCDEFGHIJKLMNO", 0),  # All letters
        ("27ABCDE1234F1Z", 0),   # Too short
        ("27ABCDE1234F1Z05", 0), # Too long
        ("00ABCDE1234F1ZG", 0),  # Invalid state code (00)
        ("38ABCDE1234F1ZX", 0),  # Invalid state code (38)
        ("27ABCDE1234F1Y2", 0),  # Missing 'Z' at position 14
        ("27ABCDE1234F1Z", 0),   # Missing checksum
        ("27ABCDE1234F1Z0", 1),  # Valid GSTIN
    ],
)
def test_gstin_validation(text, expected_len, recognizer, entities):
    """Test GSTIN validation logic."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len


@pytest.mark.parametrize(
    "gstin, expected",
    [
        # Valid GSTINs
        ("27ABCDE1234F1Z0", True),
        ("07PQRST6789K1ZY", True),
        ("01ABCDE1234F1ZE", True),
        ("37ABCDE1234F1ZZ", True),
        
        # Invalid GSTINs
        ("27ABCDE1234F1Z", False),   # Too short
        ("27ABCDE1234F1Z05", False), # Too long
        ("00ABCDE1234F1ZG", False),  # Invalid state code
        ("38ABCDE1234F1ZX", False),  # Invalid state code
        ("27ABCDE1234F1Y2", False),  # Missing 'Z' at position 14
        ("27ABCDE1234F1Z", False),   # Missing checksum
        ("27ABCDE1234F1Z0", True),   # Valid
        ("27ABCDE1234F1Z0", True),   # Valid with different case
    ],
)
def test_validate_result(gstin, expected, recognizer):
    """Test the validate_result method directly."""
    result = recognizer.validate_result(gstin)
    assert result == expected


@pytest.mark.parametrize(
    "pan, expected",
    [
        # Valid PAN formats
        ("ABCDE1234F", True),
        ("PQRST6789K", True),
        ("ABCDE1234F", True),
        
        # Invalid PAN formats
        ("ABCD1234F", False),   # Too short
        ("ABCDE12345F", False), # Too long
        ("12345ABCDE", False),  # Numbers first
        ("ABCDE1234", False),   # Missing last letter
        ("ABCDE1234F", True),   # Valid
    ],
)
def test_validate_pan_format(pan, expected, recognizer):
    """Test PAN format validation within GSTIN."""
    result = recognizer._validate_pan_format(pan)
    assert result == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("27ABCDE1234F1Z0", "27ABCDE1234F1Z0"),
        ("27ABCDE1234F1Z0", "27ABCDE1234F1Z0"),
        ("27-ABCDE-1234-F1-Z0", "27ABCDE1234F1Z0"),
        ("27 ABCDE 1234 F1 Z0", "27ABCDE1234F1Z0"),
        ("The company GSTIN is 27ABCDE1234F1Z0 for tax purposes", "27ABCDE1234F1Z0"),
    ],
)
def test_sanitize_value(text, expected, recognizer):
    """Test value sanitization."""
    result = recognizer._sanitize_value(text)
    assert result == expected


def test_gstin_recognizer_initialization():
    """Test GSTIN recognizer initialization with default parameters."""
    recognizer = InGstinRecognizer()
    
    assert recognizer.supported_entity == "IN_GSTIN"
    assert recognizer.supported_language == "en"
    assert len(recognizer.patterns) == 3
    assert len(recognizer.context) == 6
    assert "gstin" in recognizer.context
    assert "gst" in recognizer.context


def test_gstin_recognizer_with_custom_params():
    """Test GSTIN recognizer initialization with custom parameters."""
    custom_context = ["custom", "context"]
    recognizer = InGstinRecognizer(
        context=custom_context,
        supported_language="hi",
        supported_entity="CUSTOM_GSTIN"
    )
    
    assert recognizer.supported_entity == "CUSTOM_GSTIN"
    assert recognizer.supported_language == "hi"
    assert recognizer.context == custom_context


def test_gstin_recognizer_replacement_pairs():
    """Test GSTIN recognizer with custom replacement pairs."""
    custom_replacement_pairs = [("-", ""), (" ", ""), (".", "")]
    recognizer = InGstinRecognizer(replacement_pairs=custom_replacement_pairs)
    
    assert recognizer.replacement_pairs == custom_replacement_pairs
    
    # Test sanitization with custom replacement pairs
    result = recognizer._sanitize_value("27-ABCDE-1234-F1-Z0")
    assert result == "27ABCDE1234F1Z0"


@pytest.mark.parametrize(
    "gstin, expected",
    [
        # Published example value (python-stdnum's documentation)
        ("27AAPFU0939F1ZV", True),
        ("27aapfu0939f1zv", True),
        # Same structure, wrong check character
        ("27AAPFU0939F1ZA", False),
        ("27AAPFU0939F1Z5", False),
        # Adjacent characters swapped in the body
        ("27AAFPU0939F1ZV", False),
    ],
)
def test_validate_result_checks_check_character(gstin, expected, recognizer):
    """The 15th character must be the Luhn mod 36 check character."""
    assert recognizer.validate_result(gstin) == expected


def test_lookalike_with_wrong_check_character_is_not_flagged(recognizer, entities):
    """A GSTIN-shaped token with a wrong check character is not a GSTIN."""
    results = recognizer.analyze("Order ref 27AAPFU0939F1ZA shipped", entities)
    assert results == []


@pytest.mark.parametrize(
    "first_fourteen, expected",
    [
        ("27AAPFU0939F1Z", "V"),
        ("27ABCDE1234F1Z", "0"),
        ("07PQRST6789K1Z", "Y"),
        ("27AAPFU0939F1!", None),
    ],
)
def test_check_character(first_fourteen, expected):
    """Luhn mod 36 over the first 14 characters."""
    assert InGstinRecognizer._check_character(first_fourteen) == expected


def test_loads_from_default_recognizers_yaml_and_detects():
    """Enabled through the shipped YAML entry, the recognizer detects a GSTIN."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "InGstinRecognizer"]
    assert len(entries) == 1, "InGstinRecognizer missing from YAML"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entries[0], enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["InGstinRecognizer"]

    results = registry.recognizers[0].analyze("GSTIN: 27AAPFU0939F1ZV", ["IN_GSTIN"])
    assert len(results) == 1
    assert (results[0].start, results[0].end) == (7, 22)
    assert results[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)
