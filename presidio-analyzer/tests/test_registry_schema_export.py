"""Generated schemas and references must stay aligned with real configurations."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from jsonschema import Draft202012Validator

from presidio_analyzer import PatternRecognizer


def schema(**kwargs):
    from presidio_analyzer.input_validation import export_registry_schema

    return export_registry_schema(**kwargs)


def test_export_is_valid_json_schema_and_shipped_configuration_passes():
    exported = schema()
    Draft202012Validator.check_schema(exported)
    assert json.loads(json.dumps(exported)) == exported
    path = Path(__file__).parents[1] / "presidio_analyzer/conf/default_recognizers.yaml"
    assert (
        list(
            Draft202012Validator(exported).iter_errors(
                yaml.safe_load(path.read_text(encoding="utf-8"))
            )
        )
        == []
    )


@pytest.mark.parametrize("strict", [True, False])
def test_schema_respects_explicit_strict_unknown_key_policy(strict):
    validator = Draft202012Validator(schema())
    config = {
        "strict": strict,
        "recognizers": [{"class_name": "CreditCardRecognizer", "typo": 1}],
    }
    assert validator.is_valid(config) is (not strict)


@pytest.mark.parametrize(
    "entry",
    [
        "CreditCardRecognizer",
        {"class_name": "CreditCardRecognizer"},
        {"name": "alias", "class_name": "CreditCardRecognizer"},
        {"name": "custom", "supported_entities": ["TEST"], "deny_list": ["REF1234"]},
        {
            "type": "predefined",
            "class_name": "CreditCardRecognizer",
            "patterns": [{"name": "pattern", "regex": r"\b4\d{15}\b", "score": 0.5}],
        },
    ],
)
def test_schema_accepts_legacy_and_derived_identity_forms(entry):
    assert Draft202012Validator(schema(strict=True)).is_valid(
        {"supported_languages": ["en"], "recognizers": [entry]}
    )


def test_model_option_contents_remain_opaque_but_the_block_must_be_a_mapping():
    validator = Draft202012Validator(schema(strict=True))
    entry = {"class_name": "GLiNERRecognizer", "model_kwargs": {"future_option": False}}
    assert validator.is_valid({"recognizers": [entry]})
    assert not validator.is_valid(
        {"recognizers": [{**entry, "model_kwargs": "invalid"}]}
    )


def test_new_constructor_field_appears_without_registration_or_model_loading(
    monkeypatch,
):
    class SchemaOptionRecognizer(PatternRecognizer):
        def __init__(self, new_option="default", **kwargs):
            self.new_option = new_option
            super().__init__(supported_entity="TEST", deny_list=["REF1234"], **kwargs)

    load = MagicMock(side_effect=AssertionError("Schema export loaded a model"))
    monkeypatch.setattr(SchemaOptionRecognizer, "load", load)
    exported = schema(recognizer_classes=[SchemaOptionRecognizer], strict=True)
    assert Draft202012Validator(exported).is_valid(
        {
            "recognizers": [
                {"class_name": "SchemaOptionRecognizer", "new_option": {"opaque": True}}
            ]
        }
    )
    load.assert_not_called()


def test_generated_reference_is_current():
    script = (
        Path(__file__).parents[2]
        / "docs/samples/python/generate_recognizer_config_reference.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_schema_export_human_workflow_runs_from_the_standalone_script():
    script = (
        Path(__file__).parents[2] / "docs/samples/python/recognizer_config_workflows.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), "--schema"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1] == (
        "PASS: export editor schema, reject typo, correct and validate configuration"
    )


@pytest.mark.parametrize(
    "entry",
    [
        "LangExtractRecognizer",
        "PatternRecognizer",
        {"class_name": "PatternRecognizer"},
    ],
)
def test_missing_required_constructor_input_is_not_hidden_by_shorthand(entry):
    assert not Draft202012Validator(schema()).is_valid({"recognizers": [entry]})


@pytest.mark.parametrize(
    "country,expected", [("US", True), (" us ", True), ("de", False)]
)
def test_static_country_contract_is_reflected_in_schema(country, expected):
    assert (
        Draft202012Validator(schema()).is_valid(
            {
                "recognizers": [
                    {"class_name": "UsSsnRecognizer", "country_code": country}
                ]
            }
        )
        is expected
    )


def test_schema_rejects_country_metadata_on_an_untagged_predefined_class():
    assert not Draft202012Validator(schema()).is_valid(
        {"recognizers": [{"class_name": "CreditCardRecognizer", "country_code": "us"}]}
    )
