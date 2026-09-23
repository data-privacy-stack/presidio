"""Constructor-derived YAML acceptance, diagnostics, and class-local rules."""

import warnings
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from presidio_analyzer import PatternRecognizer
from presidio_analyzer.input_validation import ConfigurationValidator
from presidio_analyzer.predefined_recognizers.ner import gliner_recognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from pydantic import BaseModel, model_validator


class DerivedOptionRecognizer(PatternRecognizer):
    def __init__(
        self,
        name="DerivedOptionRecognizer",
        supported_language="en",
        custom_option="constructor-default",
        context=None,
    ):
        self.custom_option = custom_option
        super().__init__(
            supported_entity="DERIVED_EXAMPLE",
            name=name,
            supported_language=supported_language,
            context=context,
            deny_list=["REF1234"],
        )


class ForwardingOptionRecognizer(DerivedOptionRecognizer):
    def __init__(self, leaf_option=None, **kwargs):
        self.leaf_option = leaf_option
        super().__init__(**kwargs)


def config(entry, strict=False):
    return {"supported_languages": ["en"], "strict": strict, "recognizers": [entry]}


@pytest.mark.parametrize(
    "class_name", ["DerivedOptionRecognizer", "ForwardingOptionRecognizer"]
)
@pytest.mark.parametrize("value", ["non-default", 0, False, [], {"opaque": True}])
def test_new_constructor_options_reach_provider_without_a_central_schema_entry(
    class_name, value
):
    provider = RecognizerRegistryProvider(
        registry_configuration=config(
            {"name": class_name, "custom_option": value}, True
        )
    )
    recognizer = provider.create_recognizer_registry().recognizers[0]
    assert recognizer.custom_option == value
    assert type(recognizer.custom_option) is type(value)
    results = recognizer.analyze("Record REF1234.", entities=["DERIVED_EXAMPLE"])
    assert [(r.start, r.end, r.score) for r in results] == [(7, 14, 1.0)]


def test_derived_model_preserves_omitted_constructor_default():
    recognizer = (
        RecognizerRegistryProvider(
            registry_configuration=config({"name": "DerivedOptionRecognizer"}, True)
        )
        .create_recognizer_registry()
        .recognizers[0]
    )
    assert recognizer.custom_option == "constructor-default"


def test_unknown_key_warns_with_suggestion_and_accepted_keys_without_values(caplog):
    with pytest.warns(DeprecationWarning, match="custom_optino"):
        provider = RecognizerRegistryProvider(
            registry_configuration=config(
                {"name": "DerivedOptionRecognizer", "custom_optino": "value-not-logged"}
            )
        )
    recognizer = provider.create_recognizer_registry().recognizers[0]
    assert recognizer.custom_option == "constructor-default"
    assert "custom_option" in caplog.text
    assert "Accepted" in caplog.text
    assert "value-not-logged" not in caplog.text


def test_strict_unknown_key_fails_before_constructor(monkeypatch):
    load = MagicMock()
    monkeypatch.setattr(DerivedOptionRecognizer, "load", load)
    with pytest.raises(ValueError) as exc:
        RecognizerRegistryProvider(
            registry_configuration=config(
                {
                    "name": "DerivedOptionRecognizer",
                    "custom_optino": "value-not-logged",
                },
                True,
            )
        )
    message = str(exc.value) + str(exc.value.__cause__)
    assert "custom_optino" in message and "custom_option" in message
    load.assert_not_called()


def test_class_local_config_model_applies_cross_field_validation():
    class OptionRules(BaseModel):
        @model_validator(mode="before")
        @classmethod
        def validate_options(cls, values):
            if values.get("left") and values.get("right"):
                raise ValueError("left and right cannot be combined")
            return values

    class LocalRulesRecognizer(DerivedOptionRecognizer):
        CONFIG_MODEL = OptionRules

        def __init__(self, left=False, right=False, **kwargs):
            self.left = left
            self.right = right
            super().__init__(**kwargs)

    registry = RecognizerRegistryProvider(
        registry_configuration=config(
            {"name": "LocalRulesRecognizer", "left": True}, True
        )
    ).create_recognizer_registry()
    assert registry.recognizers[0].left is True
    with pytest.raises(ValueError) as exc:
        RecognizerRegistryProvider(
            registry_configuration=config(
                {"name": "LocalRulesRecognizer", "left": True, "right": True}, True
            )
        )
    assert "left and right" in str(exc.value) + str(exc.value.__cause__)


def test_gliner_flat_options_warn_and_forward_but_strict_rejects(monkeypatch):
    library = MagicMock()
    monkeypatch.setattr(gliner_recognizer, "GLiNER", library)
    entry = {"name": "GLiNERRecognizer", "local_files_only": True}
    with pytest.warns(DeprecationWarning, match="model_kwargs"):
        RecognizerRegistryProvider(
            registry_configuration=config(entry)
        ).create_recognizer_registry()
    assert library.from_pretrained.call_args.kwargs["local_files_only"] is True
    with pytest.raises(ValueError) as exc:
        RecognizerRegistryProvider(registry_configuration=config(entry, True))
    assert "local_files_only" in str(exc.value) + str(exc.value.__cause__)


def test_compatibility_catchall_does_not_expose_unused_parent_constructor_options():
    with pytest.raises(ValueError) as exc:
        RecognizerRegistryProvider(
            registry_configuration=config(
                {
                    "name": "BasicLangExtractRecognizer",
                    "enabled": False,
                    "extract_params": {"ignored": True},
                },
                True,
            )
        )
    assert "extract_params" in str(exc.value) + str(exc.value.__cause__)


def test_generic_constructor_option_defaults_are_not_added_to_dump():
    validated = ConfigurationValidator.validate_recognizer_registry_configuration(
        config({"name": "DerivedOptionRecognizer"}, True)
    )
    assert "custom_option" not in validated["recognizers"][0]


def test_custom_pattern_constructor_kwargs_reach_provider():
    recognizer = (
        RecognizerRegistryProvider(
            registry_configuration=config(
                {
                    "name": "CustomRef",
                    "supported_entity": "REFERENCE",
                    "deny_list": ["REF1234"],
                    "version": "custom-version",
                },
                True,
            )
        )
        .create_recognizer_registry()
        .recognizers[0]
    )
    assert recognizer.version == "custom-version"


def test_shipped_registry_validates_in_strict_mode_without_loading_models():
    path = Path(__file__).parents[1] / "presidio_analyzer/conf/default_recognizers.yaml"
    configuration = yaml.safe_load(path.read_text(encoding="utf-8"))
    configuration["strict"] = True
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        validated = ConfigurationValidator.validate_recognizer_registry_configuration(
            configuration
        )
    assert len(validated["recognizers"]) == len(configuration["recognizers"])
    assert not [
        item for item in caught if issubclass(item.category, DeprecationWarning)
    ]


def test_derived_gliner_config_keeps_legacy_boolean_and_numeric_coercions():
    validated = ConfigurationValidator.validate_recognizer_registry_configuration(
        config(
            {
                "name": "GLiNERRecognizer",
                "flat_ner": "false",
                "load_onnx_model": "0",
                "threshold": "0.5",
            },
            True,
        )
    )["recognizers"][0]
    assert validated["flat_ner"] is False
    assert validated["load_onnx_model"] is False
    assert validated["threshold"] == 0.5
    assert type(validated["threshold"]) is float


def test_derived_hf_config_keeps_legacy_mapping_validation():
    with pytest.raises(ValueError):
        RecognizerRegistryProvider(
            registry_configuration=config(
                {
                    "name": "HuggingFaceNerRecognizer",
                    "model_name": "example/model",
                    "label_mapping": {"PER": 1},
                },
                True,
            )
        )


def test_custom_pattern_explicit_regex_flags_are_not_overwritten():
    recognizer = (
        RecognizerRegistryProvider(
            registry_configuration=config(
                {
                    "name": "CaseSensitive",
                    "supported_entity": "REFERENCE",
                    "deny_list": ["REF1234"],
                    "global_regex_flags": 16,
                },
                True,
            )
        )
        .create_recognizer_registry()
        .recognizers[0]
    )
    assert recognizer.global_regex_flags == 16
    assert recognizer.analyze("ref1234", entities=["REFERENCE"]) == []
    assert [
        (r.start, r.end, r.score)
        for r in recognizer.analyze("REF1234", entities=["REFERENCE"])
    ] == [(0, 7, 1.0)]


def test_missing_required_constructor_option_fails_without_loading():
    class RequiredOptionRecognizer(DerivedOptionRecognizer):
        def __init__(self, required_option, **kwargs):
            super().__init__(**kwargs)

    with pytest.raises(ValueError) as exc:
        RecognizerRegistryProvider(
            registry_configuration=config({"name": "RequiredOptionRecognizer"}, True)
        )
    assert "required_option" in str(exc.value) + str(exc.value.__cause__)


def test_derived_model_cache_normalizes_optional_arguments():
    from presidio_analyzer.input_validation.recognizer_configuration import (
        derive_config_model,
    )

    assert derive_config_model(DerivedOptionRecognizer) is derive_config_model(
        DerivedOptionRecognizer, False
    )
