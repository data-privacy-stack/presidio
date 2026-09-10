import os
import importlib
from unittest.mock import MagicMock

import pytest
import dotenv

from presidio_analyzer.predefined_recognizers import AzureHealthDeidRecognizer


@pytest.fixture(scope="module")
def import_modules():
    pytest.importorskip("azure.identity")
    pytest.importorskip("azure.health.deidentification")
    from azure.health.deidentification import DeidentificationClient
    from azure.health.deidentification.models import (
        DeidentificationContent,
        DeidentificationOperationType,
        DeidentificationResult,
    )
    from azure.identity import DefaultAzureCredential


    

def requires_env_vars():
    dotenv.load_dotenv()
    endpoint = os.getenv("AHDS_ENDPOINT", "")
    return pytest.mark.skipif(
        endpoint == "",
        reason="AHDS_ENDPOINT environment variable not set"
    )

@requires_env_vars()
def test_get_supported_entities(import_modules):
    recognizer = AzureHealthDeidRecognizer()
    supported_entities = recognizer.get_supported_entities()
    assert isinstance(supported_entities, list)
    assert "PATIENT" in supported_entities


@requires_env_vars()
def test_analyze_name(import_modules):
    recognizer = AzureHealthDeidRecognizer()
    text = "Patient name is John Doe."
    results = recognizer.analyze(text)
    assert any(r.entity_type == "PATIENT" for r in results)


@requires_env_vars()
def test_analyze_email(import_modules):
    recognizer = AzureHealthDeidRecognizer()
    text = "Contact: john.doe@example.com"
    results = recognizer.analyze(text)
    assert any(r.entity_type == "EMAIL" for r in results)


@requires_env_vars()
def test_analyze_multiple_entities(import_modules):
    """Test that multiple entities are recognized in a single text."""
    recognizer = AzureHealthDeidRecognizer()
    text = "Dr. Smith met Jane Doe on 2023-01-01. Email: jane@example.com"
    results = recognizer.analyze(text)
    found_types = {r.entity_type for r in results}
    assert "DOCTOR" in found_types
    assert "DATE" in found_types
    assert "EMAIL" in found_types


@requires_env_vars()
def test_analyze_with_supported_entities_filter(import_modules):
    recognizer = AzureHealthDeidRecognizer(supported_entities=["EMAIL"])
    text = "Contact: john.doe@example.com"
    results = recognizer.analyze(text)
    assert all(r.entity_type == "EMAIL" for r in results)


@requires_env_vars()
def test_mocked_entities_match_recognizer_results():
    try:
        importlib.import_module("azure.health.deidentification")
    except ImportError:
        pytest.skip("Skipping test because 'azure.health.deidentification' is not installed")

    # Mocking the DeidentificationClient and its analyze method
    from presidio_analyzer.predefined_recognizers import AzureHealthDeidRecognizer

    class MockResult:
        def __init__(self, entity_type, start, end, score):
            self.entity_type = entity_type
            self.start = start
            self.end = end
            self.score = score

    mock_entities = [
        MockResult(entity_type="PATIENT", start=14, end=17, score=1.0),
        MockResult(entity_type="EMAIL", start=29, end=41, score=1.0)
    ]

    mock_client = MagicMock()
    mock_client.analyze = MagicMock(return_value=mock_entities)

    recognizer = AzureHealthDeidRecognizer(client=mock_client)
    results = recognizer.analyze(text="Patient Info: Raj's email is ab@email.com")

    for expected, actual in zip(mock_entities, results):
        assert expected.entity_type == actual.entity_type
        assert expected.start == actual.start
        assert expected.end == actual.end
        assert expected.score >= actual.score
