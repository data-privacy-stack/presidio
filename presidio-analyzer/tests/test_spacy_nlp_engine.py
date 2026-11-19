import json
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
import spacy

from presidio_analyzer.nlp_engine import (
    NerModelConfiguration,
    NlpEngineProvider,
    SpacyNlpEngine,
)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def test_simple_process_text(spacy_nlp_engine):
    nlp_artifacts = spacy_nlp_engine.process_text("simple text", language="en")
    assert len(nlp_artifacts.tokens) == 2
    assert not nlp_artifacts.entities
    assert nlp_artifacts.lemmas[0] == "simple"
    assert nlp_artifacts.lemmas[1] == "text"



def test_process_batch_strings(spacy_nlp_engine):
    nlp_artifacts_batch = spacy_nlp_engine.process_batch(
        ["simple text", "simple text"], language="en"
    )
    assert isinstance(nlp_artifacts_batch, Iterator)
    nlp_artifacts_batch = list(nlp_artifacts_batch)

    for text, nlp_artifacts in nlp_artifacts_batch:
        assert text == "simple text"
        assert len(nlp_artifacts.tokens) == 2


def test_nlp_not_loaded_value_error():
    unloaded_spacy_nlp = SpacyNlpEngine()
    with pytest.raises(ValueError):
        unloaded_spacy_nlp.process_text(
            "This should fail as the NLP model isn't loaded", language="en"
        )


def test_validate_model_params_missing_fields():
    model = {"lang_code": "en", "model_name": "en_core_web_lg"}

    for key in model.keys():
        new_model = model.copy()
        del new_model[key]

        with pytest.raises(ValueError):
            SpacyNlpEngine._validate_model_params(new_model)


def test_default_configuration_correct():
    spacy_nlp_engine = SpacyNlpEngine()
    expected_ner_config = NerModelConfiguration()

    actual_config_json = json.dumps(
        spacy_nlp_engine.ner_model_configuration.to_dict(),
        sort_keys=True,
        cls=SetEncoder,
    )

    expected_config_json = json.dumps(
        expected_ner_config.to_dict(), sort_keys=True, cls=SetEncoder
    )

    assert actual_config_json == expected_config_json


def test_get_supported_entities_doesnt_include_ignored():
    ner_config = NerModelConfiguration(labels_to_ignore=["A","B"],
                                       model_to_presidio_entity_mapping=dict(A="A",
                                                                             B="B",
                                                                             C="C"))
    spacy_nlp_engine = SpacyNlpEngine(ner_model_configuration=ner_config)
    entities = spacy_nlp_engine.get_supported_entities()

    assert "A" not in entities
    assert "B" not in entities
    assert "C" in entities


@pytest.mark.parametrize("texts, as_tuples", [
    (["simple text", "simple text"], False),
    ([("simple text", {"key": "value"})], True),
])
def test_batch_processing_with_as_tuples_returns_context(spacy_nlp_engine, texts, as_tuples):
    nlp_artifacts_batch = spacy_nlp_engine.process_batch(
        texts, language="en", as_tuples=as_tuples
    )
    assert isinstance(nlp_artifacts_batch, Iterator)
    nlp_artifacts_batch = list(nlp_artifacts_batch)

    if as_tuples:
        for text, nlp_artifacts, context in nlp_artifacts_batch:
            assert text == "simple text"
            assert len(nlp_artifacts.tokens) == 2
            assert context == {"key": "value"}
    else:
        for text, nlp_artifacts in nlp_artifacts_batch:
            assert text == "simple text"
            assert len(nlp_artifacts.tokens) == 2


def test_when_gpu_available_then_spacy_gpu_configured():
    """Test that spaCy GPU is configured when GPU is detected."""
    with patch("presidio_analyzer.nlp_engine.spacy_nlp_engine.device_detector") as mock_detector:
        mock_detector.get_device.return_value = "cuda"
        
        with patch("presidio_analyzer.nlp_engine.spacy_nlp_engine.spacy") as mock_spacy:
            mock_spacy.load.return_value = MagicMock()
            mock_spacy.util.is_package.return_value = True
            
            engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_sm"}])
            engine.load()
            
            mock_spacy.require_gpu.assert_called_once()


def test_when_gpu_configuration_fails_then_warning_logged():
    """Test that warning is logged when GPU configuration fails."""
    with patch("presidio_analyzer.nlp_engine.spacy_nlp_engine.device_detector") as mock_detector:
        mock_detector.get_device.return_value = "cuda"
        
        with patch("presidio_analyzer.nlp_engine.spacy_nlp_engine.spacy") as mock_spacy:
            mock_spacy.load.return_value = MagicMock()
            mock_spacy.util.is_package.return_value = True
            mock_spacy.require_gpu.side_effect = Exception("GPU error")
            
            with patch("presidio_analyzer.nlp_engine.spacy_nlp_engine.logger") as mock_logger:
                engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_sm"}])
                engine.load()
                
                assert mock_logger.warning.called


def test_when_cpu_device_then_gpu_not_configured():
    """Test that GPU is not configured when CPU device is detected."""
    with patch("presidio_analyzer.nlp_engine.spacy_nlp_engine.device_detector") as mock_detector:
        mock_detector.get_device.return_value = "cpu"
        
        with patch("presidio_analyzer.nlp_engine.spacy_nlp_engine.spacy") as mock_spacy:
            mock_spacy.load.return_value = MagicMock()
            mock_spacy.util.is_package.return_value = True
            
            engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_sm"}])
            engine.load()
            
            mock_spacy.require_gpu.assert_not_called()


@pytest.fixture(scope="module")
def spacy_nlp_engine_with_max_length(tmp_path_factory):
    """Create a spaCy NLP engine with max_length set in a YAML conf file."""
    conf_file = tmp_path_factory.mktemp("conf") / "spacy_max_length.yaml"
    conf_file.write_text(
        """
nlp_engine_name: spacy
models:
  - lang_code: en
    model_name: en_core_web_lg
    max_length: 20
"""
    )
    return NlpEngineProvider(conf_file=conf_file).create_engine()


def test_when_text_longer_than_max_length_then_process_text_raises(
    spacy_nlp_engine_with_max_length,
):
    with pytest.raises(ValueError, match="E088"):
        spacy_nlp_engine_with_max_length.process_text("a" * 21, language="en")


def test_when_text_not_longer_than_max_length_then_process_text_succeeds(
    spacy_nlp_engine_with_max_length,
):
    nlp_artifacts = spacy_nlp_engine_with_max_length.process_text(
        "a" * 20, language="en"
    )

    assert len(nlp_artifacts.tokens) == 1


def test_when_text_longer_than_max_length_then_process_batch_raises(
    spacy_nlp_engine_with_max_length,
):
    nlp_artifacts_batch = spacy_nlp_engine_with_max_length.process_batch(
        ["simple text", "a" * 21], language="en"
    )

    with pytest.raises(ValueError, match="E088"):
        list(nlp_artifacts_batch)


def test_when_max_length_not_set_then_spacy_default_is_kept(spacy_nlp_engine):
    default_max_length = spacy.blank("en").max_length

    assert spacy_nlp_engine.get_nlp("en").max_length == default_max_length


@pytest.mark.parametrize("max_length", [0, -1, 1.5, "100", True])
def test_when_max_length_is_invalid_then_load_raises(max_length):
    nlp_engine = SpacyNlpEngine(
        models=[
            {
                "lang_code": "en",
                "model_name": "en_core_web_lg",
                "max_length": max_length,
            }
        ]
    )

    with pytest.raises(ValueError, match="max_length must be a positive integer"):
        nlp_engine.load()
