"""Regression coverage for omitted versus explicitly configured settings."""

from copy import deepcopy

import pytest
import yaml

from presidio_analyzer import AnalyzerEngine, PatternRecognizer
from presidio_analyzer.analyzer_engine_provider import AnalyzerEngineProvider
from presidio_analyzer.input_validation import ConfigurationValidator
from presidio_analyzer.input_validation.yaml_recognizer_models import (
    PredefinedRecognizerConfig,
)
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


class ConfigDefaultsRecognizer(PatternRecognizer):
    """Synthetic recognizer whose defaults make accidental overrides observable."""

    def __init__(
        self,
        name="ConfigDefaultsRecognizer",
        supported_language="en",
        context=None,
    ):
        super().__init__(
            name=name,
            supported_entity="CONFIG_EXAMPLE",
            supported_language=supported_language,
            context=context,
            deny_list=["REF1234"],
            deny_list_score=0.65,
        )
        self.score_thresholds = {"CONFIG_EXAMPLE": 0.7}


@pytest.mark.parametrize(
    "overrides,expected_thresholds,expected_results",
    [
        ({}, {"CONFIG_EXAMPLE": 0.7}, []),
        ({"score_thresholds": {}}, {}, [("CONFIG_EXAMPLE", 7, 14, 0.65)]),
        ({"score_thresholds": None}, {}, [("CONFIG_EXAMPLE", 7, 14, 0.65)]),
        (
            {"score_thresholds": {"CONFIG_EXAMPLE": 0.6}},
            {"CONFIG_EXAMPLE": 0.6},
            [("CONFIG_EXAMPLE", 7, 14, 0.65)],
        ),
        (
            {"score_thresholds": {"CONFIG_EXAMPLE": 0.7}},
            {"CONFIG_EXAMPLE": 0.7},
            [],
        ),
    ],
)
@pytest.mark.parametrize("source", ["yaml", "dict"])
def test_provider_preserves_omissions_and_applies_explicit_thresholds(
    tmp_path, source, overrides, expected_thresholds, expected_results
):
    configuration = {
        "supported_languages": ["en"],
        "recognizers": [{"name": "ConfigDefaultsRecognizer", **overrides}],
    }
    original = deepcopy(configuration)
    if source == "yaml":
        path = tmp_path / "recognizers.yaml"
        path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
        provider = RecognizerRegistryProvider(conf_file=path)
    else:
        provider = RecognizerRegistryProvider(registry_configuration=configuration)

    registry = provider.create_recognizer_registry()
    assert len(registry.recognizers) == 1
    assert registry.recognizers[0].score_thresholds == expected_thresholds
    assert configuration == original
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
    )
    results = analyzer.analyze("Record REF1234.", language="en")
    assert [
        (result.entity_type, result.start, result.end, result.score)
        for result in results
    ] == expected_results
    assert analyzer.analyze("Record REF123X.", language="en") == []


@pytest.mark.parametrize(
    "entry",
    [
        {"name": "CreditCardRecognizer"},
        {
            "name": "Titles",
            "supported_entity": "TITLE",
            "deny_list": ["Dr."],
        },
        {
            "name": "HuggingFaceNerRecognizer",
            "model_name": "example/model",
            "enabled": False,
        },
        {
            "name": "GLiNERRecognizer",
            "model_name": "example/model",
            "enabled": False,
        },
    ],
)
def test_validation_does_not_materialize_omitted_recognizer_fields(entry):
    configuration = {"supported_languages": ["en"], "recognizers": [entry]}
    validated = ConfigurationValidator.validate_recognizer_registry_configuration(
        configuration
    )
    assert set(validated["recognizers"][0]) == set(entry) | {"type", "enabled"}
    assert validated["global_regex_flags"] == 26
    assert validated["supported_languages"] == ["en"]


@pytest.mark.parametrize("class_name", ["HuggingFaceNerRecognizer", "GLiNERRecognizer"])
def test_validation_preserves_explicit_null_threshold_for_model_recognizers(class_name):
    configuration = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": class_name,
                "enabled": False,
                "model_name": "example/model",
                "score_thresholds": None,
            }
        ],
    }
    validated = ConfigurationValidator.validate_recognizer_registry_configuration(
        configuration
    )
    entry = validated["recognizers"][0]
    assert "score_thresholds" in entry
    assert entry["score_thresholds"] is None


def test_provider_keeps_inferred_type_when_given_an_existing_config_model():
    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                PredefinedRecognizerConfig(name="ConfigDefaultsRecognizer")
            ],
        }
    )
    recognizer = provider.create_recognizer_registry().recognizers[0]
    assert isinstance(recognizer, ConfigDefaultsRecognizer)
    assert recognizer.score_thresholds == {"CONFIG_EXAMPLE": 0.7}


def test_analyzer_provider_keeps_defaults_from_inline_registry_yaml(tmp_path):
    configuration = {
        "supported_languages": ["en"],
        "nlp_configuration": {
            "nlp_engine_name": "no_op",
            "models": [{"lang_code": "en", "model_name": "no_op"}],
        },
        "recognizer_registry": {
            "recognizers": [{"name": "ConfigDefaultsRecognizer"}],
        },
    }
    path = tmp_path / "analyzer.yaml"
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    analyzer = AnalyzerEngineProvider(analyzer_engine_conf_file=path).create_engine()
    assert analyzer.registry.recognizers[0].score_thresholds == {"CONFIG_EXAMPLE": 0.7}
    assert analyzer.analyze("Record REF1234.", language="en") == []
