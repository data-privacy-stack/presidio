"""Dry-run diagnostics must be actionable, value-safe and model-free."""

from unittest.mock import MagicMock

import pytest
import yaml
from pydantic import BaseModel, model_validator

from presidio_analyzer import PatternRecognizer


def validate(config, **kwargs):
    from presidio_analyzer.input_validation import validate_registry_config

    return validate_registry_config(config, **kwargs)


def test_valid_registry_can_be_checked_from_mapping_or_file_without_loading(
    tmp_path, monkeypatch
):
    from presidio_analyzer.chunkers import TextChunkerProvider
    from presidio_analyzer.predefined_recognizers import (
        GLiNERRecognizer,
        HuggingFaceNerRecognizer,
    )

    load = MagicMock(side_effect=AssertionError("Dry-run loaded a model"))
    monkeypatch.setattr(GLiNERRecognizer, "load", load)
    monkeypatch.setattr(HuggingFaceNerRecognizer, "load", load)
    monkeypatch.setattr(TextChunkerProvider, "create_chunker", load)
    config = {
        "recognizers": [
            {"name": "GLiNERRecognizer", "model_name": "example/gliner"},
            {
                "name": "HuggingFaceNerRecognizer",
                "model_name": "example/hf",
                "text_chunker": {"chunker_type": "tokenizer", "tokenizer": "uncached"},
            },
        ]
    }
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert validate(config) == []
    assert validate(path) == []
    load.assert_not_called()


def test_strict_typo_diagnostic_names_the_key_suggestion_and_entry_not_value():
    errors = validate(
        {
            "recognizers": [
                {
                    "name": "CreditCardRecognizer",
                    "replacement_paris": "secret-option-value",
                }
            ]
        },
        strict=True,
    )
    assert len(errors) == 1
    assert errors[0].path == ("recognizers", 0, "replacement_paris")
    assert errors[0].code == "unknown_key"
    assert "replacement_pairs" in errors[0].message
    assert "secret-option-value" not in repr(errors)


def test_multiple_invalid_entries_are_reported_with_distinct_paths():
    errors = validate(
        {
            "strict": True,
            "recognizers": [
                {"name": "CreditCardRecognizer", "typo": 1},
                {"name": "CreditCardRecognizer", "score_thresholds": {"default": 2}},
            ],
        }
    )
    assert [error.path[:2] for error in errors] == [
        ("recognizers", 0),
        ("recognizers", 1),
    ]


def test_duplicate_identity_is_a_preload_diagnostic():
    errors = validate({"recognizers": ["CreditCardRecognizer", "CreditCardRecognizer"]})
    assert len(errors) == 1
    assert errors[0].code == "duplicate_identity"
    assert errors[0].path == ("recognizers", 1)
    assert "distinct names" in errors[0].message


@pytest.mark.parametrize("value", ["TOP-SECRET", {"TOP-SECRET": 1}])
def test_threshold_diagnostics_do_not_echo_invalid_values(value):
    errors = validate(
        {
            "recognizers": [
                {"name": "CreditCardRecognizer", "score_thresholds": {"default": value}}
            ]
        }
    )
    assert errors[0].path == ("recognizers", 0, "score_thresholds", "default")
    assert "numeric" in errors[0].message
    assert "TOP-SECRET" not in repr(errors)


def test_unknown_custom_validator_error_is_not_treated_as_value_safe():
    class SecretRules(BaseModel):
        @model_validator(mode="before")
        @classmethod
        def reject(cls, values):
            raise ValueError(f"Rejected secret: {values['token']}")

    class SecretConfigurationRecognizer(PatternRecognizer):
        CONFIG_MODEL = SecretRules

        def __init__(self, token, **kwargs):
            super().__init__(supported_entity="TEST", deny_list=["REF1234"], **kwargs)

    errors = validate(
        {
            "recognizers": [
                {
                    "class_name": SecretConfigurationRecognizer.__name__,
                    "token": "TOP-SECRET",
                }
            ]
        }
    )
    assert [(error.code, error.path) for error in errors] == [
        ("value_error", ("recognizers", 0))
    ]
    assert "TOP-SECRET" not in repr(errors)


def test_block_collision_diagnostic_is_value_safe_and_names_the_block():
    errors = validate(
        {
            "recognizers": [
                {
                    "name": "GLiNERRecognizer",
                    "model_kwargs": {"threshold": "TOP-SECRET"},
                }
            ]
        }
    )
    assert errors[0].path == ("recognizers", 0, "model_kwargs")
    assert "threshold" in errors[0].message
    assert "TOP-SECRET" not in repr(errors)


@pytest.mark.parametrize(
    "config,code",
    [([], "mapping_type"), ({1: "secret"}, "mapping_keys"), ({}, "value_error")],
)
def test_invalid_root_is_reported_not_defaulted(config, code):
    errors = validate(config)
    assert errors
    assert errors[0].code == code


def test_missing_file_returns_error_instead_of_shipped_defaults(tmp_path):
    errors = validate(tmp_path / "missing.yaml")
    assert errors[0].code == "file_read"


def test_invalid_yaml_diagnostic_excludes_source_contents(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("recognizers: [TOP-SECRET", encoding="utf-8")
    errors = validate(path)
    assert errors[0].code == "yaml_syntax"
    assert "TOP-SECRET" not in repr(errors)


def test_unknown_keys_keep_compatibility_warnings_when_strict_is_not_requested():
    with pytest.warns(DeprecationWarning, match="typo"):
        assert (
            validate({"recognizers": [{"name": "CreditCardRecognizer", "typo": 1}]})
            == []
        )


def test_unknown_class_suggests_registered_names_without_echoing_input():
    errors = validate({"recognizers": [{"class_name": "CreditCardRecognizr"}]})
    assert errors[0].code == "unknown_class"
    assert "CreditCardRecognizer" in errors[0].message
    assert "CreditCardRecognizr" not in errors[0].message


def test_unexpected_programming_errors_are_not_converted_to_validation_errors(
    monkeypatch,
):
    from presidio_analyzer.recognizer_registry import RecognizerFactory

    monkeypatch.setattr(
        RecognizerFactory, "create_specs", MagicMock(side_effect=RuntimeError("bug"))
    )
    with pytest.raises(RuntimeError, match="bug"):
        validate({"recognizers": ["CreditCardRecognizer"]})


def test_country_mismatch_reports_the_country_field():
    errors = validate(
        {"recognizers": [{"name": "UsSsnRecognizer", "country_code": "zz"}]}
    )
    assert errors[0].path == ("recognizers", 0, "country_code")
    assert "COUNTRY_CODE (us)" in errors[0].message


def test_union_error_locations_contain_only_input_keys():
    errors = validate(
        {"recognizers": [{"name": "IpRecognizer", "supported_languages": "en"}]}
    )
    assert [error.path for error in errors] == [
        ("recognizers", 0, "supported_languages")
    ]


def test_duplicate_valid_entries_are_reported_alongside_an_invalid_entry():
    errors = validate(
        {
            "strict": True,
            "recognizers": [
                {"name": "IpRecognizer", "typo": 1},
                "CreditCardRecognizer",
                "CreditCardRecognizer",
            ],
        }
    )
    assert [(error.code, error.path) for error in errors] == [
        ("unknown_key", ("recognizers", 0, "typo")),
        ("duplicate_identity", ("recognizers", 2)),
    ]


def test_builtin_class_resolution_uses_the_public_export_after_reload(monkeypatch):
    from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
        RecognizerListLoader,
    )

    shadow = type("PatternRecognizer", (PatternRecognizer,), {})
    monkeypatch.setattr(
        RecognizerListLoader, "get_all_existing_recognizers", lambda: {shadow}
    )
    assert (
        RecognizerListLoader.get_existing_recognizer_cls("PatternRecognizer")
        is PatternRecognizer
    )
