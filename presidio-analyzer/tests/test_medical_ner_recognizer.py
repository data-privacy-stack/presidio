import pytest
from unittest.mock import MagicMock, patch

from presidio_analyzer.predefined_recognizers.ner.medical_ner_recognizer import (
    DEFAULT_MEDICAL_ENTITY_MAPPING,
    MedicalNERRecognizer,
)
from presidio_analyzer.predefined_recognizers.ner.huggingface_ner_recognizer import (
    HuggingFaceNerRecognizer,
)


def _make_pipeline_prediction(entity_group, score, word, start, end):
    """Create a dict mimicking HuggingFace pipeline output."""
    return {
        "entity_group": entity_group,
        "score": score,
        "word": word,
        "start": start,
        "end": end,
    }


# Patches needed for every test that instantiates the recognizer:
# 1. hf_pipeline - checked in __init__, must be truthy
# 2. torch - checked in __init__, must be truthy
# 3. device_detector - called by _parse_device
_PATCH_HF = (
    "presidio_analyzer.predefined_recognizers.ner"
    ".huggingface_ner_recognizer.hf_pipeline"
)
_PATCH_TORCH = (
    "presidio_analyzer.predefined_recognizers.ner"
    ".huggingface_ner_recognizer.torch"
)
_PATCH_DEVICE = (
    "presidio_analyzer.predefined_recognizers.ner"
    ".huggingface_ner_recognizer.device_detector"
)


@pytest.fixture
def recognizer():
    """Create a MedicalNERRecognizer with a mocked pipeline."""
    with (
        patch(_PATCH_HF, new=MagicMock()),
        patch(_PATCH_TORCH, new=MagicMock()),
        patch(_PATCH_DEVICE) as mock_dd,
    ):
        mock_dd.get_device.return_value = "cpu"
        rec = MedicalNERRecognizer()
    # Replace the pipeline created by load() with a controllable mock
    rec.ner_pipeline = MagicMock()
    return rec


def _make_recognizer(**kwargs):
    """Helper to create a recognizer with all deps mocked."""
    with (
        patch(_PATCH_HF, new=MagicMock()),
        patch(_PATCH_TORCH, new=MagicMock()),
        patch(_PATCH_DEVICE) as mock_dd,
    ):
        mock_dd.get_device.return_value = "cpu"
        return MedicalNERRecognizer(**kwargs)


def test_inherits_from_huggingface_ner_recognizer(recognizer):
    """MedicalNERRecognizer should inherit from HuggingFaceNerRecognizer."""
    assert isinstance(recognizer, HuggingFaceNerRecognizer)


def test_default_entities(recognizer):
    """Default supported entities should match the 8 medical entity types."""
    expected = set(DEFAULT_MEDICAL_ENTITY_MAPPING.values())
    assert set(recognizer.supported_entities) == expected


def test_default_model_name(recognizer):
    """Default model should be blaze999/Medical-NER."""
    assert recognizer.model_name == "blaze999/Medical-NER"


def test_default_aggregation_strategy(recognizer):
    """Default aggregation_strategy should be 'simple'."""
    assert recognizer.aggregation_strategy == "simple"


def test_custom_supported_entities():
    """Users can override supported_entities to filter which types are returned."""
    rec = _make_recognizer(
        supported_entities=["MEDICAL_DISEASE_DISORDER", "MEDICAL_MEDICATION"]
    )
    assert set(rec.supported_entities) == {
        "MEDICAL_DISEASE_DISORDER",
        "MEDICAL_MEDICATION",
    }


def test_custom_label_mapping():
    """Users can provide a custom label mapping."""
    custom = {"DISEASE_DISORDER": "MY_DISEASE"}
    rec = _make_recognizer(label_mapping=custom)
    assert rec.label_mapping == custom
    assert "MY_DISEASE" in rec.supported_entities


def test_analyze_returns_matching_entities(recognizer):
    """Entities from pipeline output matching supported_entities are returned."""
    recognizer.ner_pipeline.return_value = [
        _make_pipeline_prediction("DISEASE_DISORDER", 0.95, "diabetes", 24, 32),
        _make_pipeline_prediction("MEDICATION", 0.90, "metformin", 53, 62),
    ]

    results = recognizer.analyze(
        text="The patient presents with diabetes and is prescribed metformin.",
        entities=["MEDICAL_DISEASE_DISORDER", "MEDICAL_MEDICATION"],
    )

    assert len(results) == 2
    assert results[0].entity_type == "MEDICAL_DISEASE_DISORDER"
    assert results[0].start == 24
    assert results[0].end == 32
    assert results[0].score == pytest.approx(0.95, rel=1e-2)
    assert results[1].entity_type == "MEDICAL_MEDICATION"
    assert results[1].start == 53
    assert results[1].end == 62
    assert results[1].score == pytest.approx(0.90, rel=1e-2)


def test_analyze_filters_by_requested_entities(recognizer):
    """Only entities in the requested list are returned."""
    recognizer.ner_pipeline.return_value = [
        _make_pipeline_prediction("DISEASE_DISORDER", 0.95, "Diabetes", 0, 8),
        _make_pipeline_prediction("MEDICATION", 0.90, "metformin", 22, 31),
    ]

    results = recognizer.analyze(
        text="Diabetes treated with metformin.",
        entities=["MEDICAL_DISEASE_DISORDER"],
    )

    assert len(results) == 1
    assert results[0].entity_type == "MEDICAL_DISEASE_DISORDER"


def test_analyze_unmapped_label_passthrough(recognizer):
    """Unmapped labels pass through as-is (discovery mode)."""
    recognizer.ner_pipeline.return_value = [
        _make_pipeline_prediction("UNKNOWN_LABEL", 0.80, "foo", 0, 3),
        _make_pipeline_prediction("DISEASE_DISORDER", 0.95, "diabetes", 4, 12),
    ]

    results = recognizer.analyze(
        text="foo diabetes",
        entities=["MEDICAL_DISEASE_DISORDER"],
    )

    # MEDICAL_DISEASE_DISORDER is requested + UNKNOWN_LABEL is kept (not in supported)
    entity_types = {r.entity_type for r in results}
    assert "MEDICAL_DISEASE_DISORDER" in entity_types
    # Unmapped label passes through per upstream filter policy
    assert "UNKNOWN_LABEL" in entity_types


def test_analyze_empty_text(recognizer):
    """Empty text should return no results."""
    results = recognizer.analyze(text="", entities=["MEDICAL_DISEASE_DISORDER"])
    assert results == []


def test_analyze_whitespace_text(recognizer):
    """Whitespace-only text should return no results."""
    results = recognizer.analyze(text="   ", entities=["MEDICAL_DISEASE_DISORDER"])
    assert results == []


def test_analyze_no_predictions(recognizer):
    """Pipeline returning no predictions should yield empty results."""
    recognizer.ner_pipeline.return_value = []

    results = recognizer.analyze(
        text="No medical entities here.",
        entities=["MEDICAL_DISEASE_DISORDER"],
    )

    assert len(results) == 0


def test_explanation_text(recognizer):
    """Results should have explanation text mentioning Medical-NER model."""
    recognizer.ner_pipeline.return_value = [
        _make_pipeline_prediction("DISEASE_DISORDER", 0.95, "Diabetes", 0, 8),
    ]

    results = recognizer.analyze(
        text="Diabetes is common.",
        entities=["MEDICAL_DISEASE_DISORDER"],
    )

    assert len(results) == 1
    explanation = results[0].analysis_explanation
    assert "Medical" in explanation.textual_explanation
    assert "MEDICAL_DISEASE_DISORDER" in explanation.textual_explanation


def test_normalize_label():
    """BIO/BIOLU prefixes should be stripped from labels."""
    rec = MagicMock(spec=HuggingFaceNerRecognizer)
    rec.label_prefixes = ["B-", "I-", "U-", "L-"]
    normalize = HuggingFaceNerRecognizer._normalize_label

    assert normalize(rec, "B-PER") == "PER"
    assert normalize(rec, "I-LOC") == "LOC"
    assert normalize(rec, "U-ORG") == "ORG"
    assert normalize(rec, "L-MISC") == "MISC"
    assert normalize(rec, "O") == "O"
    assert normalize(rec, "DISEASE_DISORDER") == "DISEASE_DISORDER"


def test_bio_prefix_in_pipeline_output(recognizer):
    """Pipeline output with BIO prefixes should be handled correctly."""
    recognizer.ner_pipeline.return_value = [
        {
            "entity": "B-DISEASE_DISORDER",
            "score": 0.95,
            "word": "Diabetes",
            "start": 0,
            "end": 8,
        },
    ]

    results = recognizer.analyze(
        text="Diabetes is common.",
        entities=["MEDICAL_DISEASE_DISORDER"],
    )

    assert len(results) == 1
    assert results[0].entity_type == "MEDICAL_DISEASE_DISORDER"


def test_threshold_filters_low_scores(recognizer):
    """Predictions below the threshold should be filtered out."""
    recognizer.ner_pipeline.return_value = [
        _make_pipeline_prediction("DISEASE_DISORDER", 0.1, "maybe", 0, 5),
        _make_pipeline_prediction("MEDICATION", 0.95, "metformin", 10, 19),
    ]

    results = recognizer.analyze(
        text="maybe not metformin",
        entities=["MEDICAL_DISEASE_DISORDER", "MEDICAL_MEDICATION"],
    )

    assert len(results) == 1
    assert results[0].entity_type == "MEDICAL_MEDICATION"
