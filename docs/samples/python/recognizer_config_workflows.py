"""Exercise configuration workflows with synthetic data and no model download.

Run from ``presidio-analyzer``:
``uv run python ../docs/samples/python/recognizer_config_workflows.py``

The script writes, loads, edits, and reloads real YAML files in a temporary
directory. Assertions describe the observable result of each user action.
"""

import argparse
import json
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from presidio_analyzer import AnalyzerEngine, PatternRecognizer
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)


class WorkflowRecognizer(PatternRecognizer):
    """Recognize a synthetic reference with a deliberately higher threshold."""

    def __init__(
        self, name="WorkflowRecognizer", supported_language="en", context=None
    ):
        super().__init__(
            name=name,
            supported_language=supported_language,
            context=context,
            supported_entity="WORKFLOW_REFERENCE",
            deny_list=["REF1234"],
            deny_list_score=0.65,
        )
        self.score_thresholds = {"WORKFLOW_REFERENCE": 0.7}


class WorkflowModelRecognizer(WorkflowRecognizer):
    """Model-free double for exercising model-aware YAML identities."""

    def __init__(self, model_name="example/default", **kwargs):
        self.model_name = model_name
        super().__init__(**kwargs)


def load_analyzer(path: Path) -> AnalyzerEngine:
    """Load the edited configuration without using an external NLP model."""
    registry = RecognizerRegistryProvider(conf_file=path).create_recognizer_registry()
    return AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
    )


def run_default_workflow(directory: Path) -> None:
    """Create, edit, and reload threshold settings as a YAML user would."""
    path = directory / "recognizers.yaml"
    entry = {"name": "WorkflowRecognizer"}
    configuration = {"supported_languages": ["en"], "recognizers": [entry]}

    for step, thresholds, expected in [
        ("omit", None, []),
        ("override", {"WORKFLOW_REFERENCE": 0.6}, [(7, 14, 0.65)]),
        ("clear", {}, [(7, 14, 0.65)]),
        ("restore", None, []),
    ]:
        if thresholds is None:
            entry.pop("score_thresholds", None)
        else:
            entry["score_thresholds"] = thresholds
        path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
        analyzer = load_analyzer(path)
        results = analyzer.analyze("Record REF1234.", language="en")
        assert [(r.start, r.end, r.score) for r in results] == expected, step
        assert analyzer.analyze("Record REF123X.", language="en") == [], step
        print(f"PASS: {step} threshold, reload YAML, detect and reject lookalike")


def run_gliner_workflow(directory: Path) -> None:
    """Load a cached GLiNER model through YAML and exercise both option blocks."""
    import torch

    torch.manual_seed(0)
    path = directory / "gliner.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "supported_languages": ["en"],
                "recognizers": [
                    {
                        "name": "GLiNERRecognizer",
                        "model_name": "urchade/gliner_multi_pii-v1",
                        "entity_mapping": {"person": "PERSON"},
                        "map_location": "cpu",
                        "threshold": 0.5,
                        "model_kwargs": {"local_files_only": True},
                        "predict_kwargs": {"return_class_probs": True},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    analyzer = load_analyzer(path)
    recognizer = analyzer.registry.recognizers[0]
    text = "My name is John Smith."
    baseline = recognizer.gliner.predict_entities(text, ["person"], threshold=0.5)
    results = analyzer.analyze(text, language="en")
    assert [(r.entity_type, r.start, r.end) for r in results] == [("PERSON", 11, 21)]
    assert [r.score for r in results] == [
        prediction["score"] for prediction in baseline
    ]
    assert analyzer.analyze("No entities in this sentence.", language="en") == []
    print("PASS: GLiNER YAML blocks, cached-model detection, exact spans and scores")


def run_huggingface_workflow(directory: Path) -> None:
    """Exercise pipeline loading and prediction options with a pinned real model."""
    import torch

    torch.manual_seed(0)
    path = directory / "huggingface.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "supported_languages": ["en"],
                "recognizers": [
                    {
                        "name": "HuggingFaceNerRecognizer",
                        "model_name": "StanfordAIMI/stanford-deidentifier-base",
                        "device": "cpu",
                        "label_mapping": {
                            "PATIENT": "PERSON",
                            "HCW": "PERSON",
                            "HOSPITAL": "ORGANIZATION",
                            "DATE": "DATE_TIME",
                            "PHONE": "PHONE_NUMBER",
                            "VENDOR": "ORGANIZATION",
                            "ID": "ID",
                        },
                        "model_kwargs": {
                            "revision": "661b9c1c717d3165512d440abc3700c386aefab6",
                            "trust_remote_code": False,
                            "model_kwargs": {"local_files_only": True},
                        },
                        "predict_kwargs": {"ignore_labels": ["O"], "batch_size": 1},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    analyzer = load_analyzer(path)
    recognizer = analyzer.registry.recognizers[0]
    text = "Patient Evelyn Johnson was seen today."
    baseline = recognizer.ner_pipeline(text, ignore_labels=["O"], batch_size=1)
    results = analyzer.analyze(text, language="en")
    assert [(r.entity_type, r.start, r.end) for r in results] == [("PERSON", 8, 22)]
    assert [r.score for r in results] == [float(p["score"]) for p in baseline]
    assert analyzer.analyze("No entities in this sentence.", language="en") == []
    print(
        "PASS: HuggingFace YAML blocks, pinned-model detection, exact spans and scores"
    )


def run_langextract_workflow(directory: Path) -> None:
    """Edit and load a LangExtract provider file without making a service request."""
    from presidio_analyzer.predefined_recognizers import BasicLangExtractRecognizer

    configuration = yaml.safe_load(
        BasicLangExtractRecognizer.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    )
    provider = configuration["langextract"]["model"]["provider"]
    provider["language_model_params"]["timeout"] = 12
    model_path = directory / "langextract-model.yaml"
    model_path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    registry_path = directory / "langextract-registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "supported_languages": ["en"],
                "recognizers": [
                    {
                        "name": "BasicLangExtractRecognizer",
                        "config_path": str(model_path),
                        "unused_setting": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        registry = RecognizerRegistryProvider(
            conf_file=registry_path
        ).create_recognizer_registry()
    recognizer = registry.recognizers[0]
    assert recognizer.provider_kwargs["timeout"] == 12
    assert any("unused_setting" in str(item.message) for item in caught)
    print(
        "PASS: LangExtract provider-file edit and ignored-key diagnostic, no service call"
    )


def run_schema_workflow(directory: Path) -> None:
    """Correct a misspelled YAML option after warning and strict rejection."""
    path = directory / "strict.yaml"
    configuration = {
        "supported_languages": ["en"],
        "recognizers": [{"name": "WorkflowRecognizer", "score_thresolds": {}}],
    }
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        load_analyzer(path)
    assert any("score_thresolds" in str(item.message) for item in caught)
    configuration["strict"] = True
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    try:
        load_analyzer(path)
    except ValueError as exc:
        assert "score_thresolds" in str(exc) + str(exc.__cause__)
    else:
        raise AssertionError("Strict validation accepted an unknown setting")
    entry = configuration["recognizers"][0]
    entry["score_thresholds"] = entry.pop("score_thresolds")
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    analyzer = load_analyzer(path)
    assert [
        (r.start, r.end, r.score)
        for r in analyzer.analyze("Record REF1234.", language="en")
    ] == [(7, 14, 0.65)]
    print("PASS: unknown-key warning, strict rejection, correction and reload")


def run_identity_workflow(directory: Path) -> None:
    """Add models, diagnose ambiguous names, rename, and reload real YAML."""
    path = directory / "identities.yaml"
    entries = [
        {
            "class_name": "WorkflowModelRecognizer",
            "model_name": f"example/{model}",
            "score_thresholds": {},
        }
        for model in ("one", "two")
    ]
    configuration = {"supported_languages": ["en"], "recognizers": entries}
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    analyzer = load_analyzer(path)
    assert [r.name for r in analyzer.registry.recognizers] == [
        "WorkflowModelRecognizer:example/one",
        "WorkflowModelRecognizer:example/two",
    ]
    entries[1]["model_name"] = "example/one"
    entries[1]["name"] = "second"
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    try:
        load_analyzer(path)
    except ValueError as exc:
        assert "explicit unique names" in str(exc) + str(exc.__cause__)
    else:
        raise AssertionError("Repeated model accepted an implicit name")
    entries[0]["name"] = "first"
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    analyzer = load_analyzer(path)
    assert [r.name for r in analyzer.registry.recognizers] == ["first", "second"]
    assert [
        (r.start, r.end, r.score)
        for r in analyzer.analyze("Record REF1234.", language="en")
    ] == [(7, 14, 0.65)]
    assert analyzer.analyze("Record REF123X.", language="en") == []
    print("PASS: derive model names, reject ambiguity, rename and reload")


def run_factory_workflow(directory: Path) -> None:
    """Switch an existing configuration between provider, file and dict APIs."""
    path = directory / "entry-points.yaml"
    entry = {
        "name": "reference",
        "supported_entities": ["WORKFLOW_REFERENCE"],
        "deny_list": ["REF1234"],
        "deny_list_score": 0.65,
        "context": ["reference"],
        "supported_languages": ["en"],
        "score_thresholds": {"default": 0.6},
    }
    path.write_text(
        yaml.safe_dump({"supported_languages": ["en"], "recognizers": [entry]}),
        encoding="utf-8",
    )
    provider_registry = RecognizerRegistryProvider(
        conf_file=path
    ).create_recognizer_registry()
    yaml_registry = RecognizerRegistry()
    yaml_registry.add_recognizers_from_yaml(path)
    dict_registry = RecognizerRegistry()
    dict_registry.add_pattern_recognizer_from_dict(entry)
    for registry in (provider_registry, yaml_registry, dict_registry):
        assert registry.recognizers[0].context == ["reference"]
        assert registry.recognizers[0].score_thresholds == {"default": 0.6}
        analyzer = AnalyzerEngine(
            registry=registry,
            nlp_engine=NoOpNlpEngine(
                models=[{"lang_code": "en", "model_name": "no_op"}]
            ),
        )
        assert [
            (r.start, r.end, r.score)
            for r in analyzer.analyze("Record REF1234.", language="en")
        ] == [(7, 14, 0.65)]
        assert analyzer.analyze("Record REF123X.", language="en") == []
    print("PASS: switch provider, YAML and dict APIs with identical detections")


def run_pattern_workflow(directory: Path) -> None:
    """Override a shipped recognizer's pattern while retaining its checksum."""
    path = directory / "patterns.yaml"
    configuration = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "class_name": "CreditCardRecognizer",
                "type": "predefined",
                "patterns": [
                    {"name": "visa-format", "regex": r"\b4\d{15}\b", "score": 0.5}
                ],
            }
        ],
    }
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    analyzer = load_analyzer(path)
    assert [
        (r.start, r.end, r.score)
        for r in analyzer.analyze("Card 4111111111111111.", language="en")
    ] == [(5, 21, 1.0)]
    assert analyzer.analyze("Card 4111111111111112.", language="en") == []
    assert analyzer.analyze("Card 5555555555554444.", language="en") == []
    configuration["recognizers"][0]["patterns"][0]["regex"] = "["
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    try:
        load_analyzer(path)
    except ValueError as exc:
        assert "regex syntax" in str(exc)
    else:
        raise AssertionError("Invalid configured pattern was accepted")
    print("PASS: override predefined patterns, preserve checksum, reject invalid edit")


def run_validation_workflow(directory: Path) -> None:
    """Lint an edited file, fix the reported key, and revalidate without loading."""
    from presidio_analyzer.input_validation import validate_registry_config

    path = directory / "validate.yaml"
    config = {
        "strict": True,
        "recognizers": [{"name": "CreditCardRecognizer", "replacement_paris": []}],
    }
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    errors = validate_registry_config(path)
    assert len(errors) == 1
    assert errors[0].path == ("recognizers", 0, "replacement_paris")
    assert "replacement_pairs" in errors[0].message
    entry = config["recognizers"][0]
    entry["replacement_pairs"] = entry.pop("replacement_paris")
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert validate_registry_config(path) == []
    assert validate_registry_config(directory / "missing.yaml")[0].code == "file_read"
    print("PASS: dry-run diagnostics, fix the reported key, revalidate without models")

    config = {
        "strict": True,
        "recognizers": [
            {"name": "IpRecognizer", "typo": 1},
            "CreditCardRecognizer",
            "CreditCardRecognizer",
        ],
    }
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    errors = validate_registry_config(path)
    assert [(error.code, error.path) for error in errors] == [
        ("unknown_key", ("recognizers", 0, "typo")),
        ("duplicate_identity", ("recognizers", 2)),
    ]
    assert errors[1].message == (
        "Duplicate recognizer identity; choose distinct names for each language."
    )
    typo, duplicate = errors
    config["recognizers"][typo.path[1]].pop(typo.path[2])
    config["recognizers"][duplicate.path[1]] = {
        "class_name": "CreditCardRecognizer",
        "name": "secondary_card",
    }
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert validate_registry_config(path) == []
    assert [
        (result.entity_type, result.start, result.end, result.score)
        for result in load_analyzer(path).analyze(
            "Card 4111111111111111.", language="en"
        )
    ] == [("CREDIT_CARD", 5, 21, 1.0)]
    config = {
        "strict": True,
        "recognizers": [
            {"name": "IpRecognizer", "typo": 1},
            {"class_name": "GLiNERRecognizer", "model_name": "example/model"},
            {
                "class_name": "GLiNERRecognizer",
                "model_name": "example/model",
                "name": "another-model",
            },
        ],
    }
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    errors = validate_registry_config(path)
    assert [(error.code, error.path) for error in errors] == [
        ("unknown_key", ("recognizers", 0, "typo")),
        ("repeated_model", ("recognizers", 1)),
    ]
    typo, unnamed = errors
    config["recognizers"][typo.path[1]].pop(typo.path[2])
    config["recognizers"][unnamed.path[1]]["name"] = "named-model"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert validate_registry_config(path) == []
    print("PASS: locate independent errors, fix original entries, reload and detect")


def run_schema_export_workflow(directory: Path) -> None:
    """Export an editor schema and correct an option rejected by that schema."""
    from jsonschema import Draft202012Validator

    from presidio_analyzer.input_validation import export_registry_schema

    path = directory / "registry.schema.json"
    path.write_text(json.dumps(export_registry_schema(strict=True)), encoding="utf-8")
    validator = Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))
    configuration = {
        "recognizers": [{"class_name": "CreditCardRecognizer", "replacement_paris": []}]
    }
    assert not validator.is_valid(configuration)
    entry = configuration["recognizers"][0]
    entry["replacement_pairs"] = entry.pop("replacement_paris")
    assert validator.is_valid(configuration)
    print("PASS: export editor schema, reject typo, correct and validate configuration")


def run_rest_workflow(directory: Path) -> None:
    """Exercise real HTTP routes with YAML reloads and no external services."""
    import importlib.util
    import os
    import sys
    from unittest.mock import patch

    root = Path(__file__).resolve().parents[3]

    def make_app(component):
        module_name = "_workflow_" + component.replace("-", "_")
        app_path = root / component / "app.py"
        if not app_path.is_file():
            raise FileNotFoundError(
                "The --rest workflow requires a complete Presidio checkout "
                "containing the Analyzer and Anonymizer applications"
            )
        spec = importlib.util.spec_from_file_location(module_name, app_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load the workflow's HTTP application")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            return module.Server().app
        finally:
            sys.modules.pop(module_name, None)

    path = directory / "http-analyzer.yaml"
    entry = {"class_name": "WorkflowRecognizer", "score_thresholds": {"default": 0.7}}
    configuration = {
        "supported_languages": ["en"],
        "nlp_configuration": {
            "nlp_engine_name": "no_op",
            "models": [{"lang_code": "en", "model_name": "no_op"}],
        },
        "recognizer_registry": {"recognizers": [entry]},
    }
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    with patch.dict(
        os.environ,
        {
            "ANALYZER_CONF_FILE": str(path),
            "NLP_CONF_FILE": "",
            "RECOGNIZER_REGISTRY_CONF_FILE": "",
            "LOG_LEVEL": "ERROR",
            "BATCH_SIZE": "500",
            "N_PROCESS": "1",
        },
    ):
        client = make_app("presidio-analyzer").test_client()
        response = client.post(
            "/analyze", json={"text": "Record REF1234.", "language": "en"}
        )
        assert response.status_code == 200
        assert response.get_json() == []

        response = client.post(
            "/analyze",
            json={"text": "Record REF1234.", "language": "en", "score_threshold": 0.6},
        )
        assert response.status_code == 200
        assert [
            (item["entity_type"], item["start"], item["end"], item["score"])
            for item in response.get_json()
        ] == [("WORKFLOW_REFERENCE", 7, 14, 0.65)]
        response = client.post(
            "/analyze",
            json={
                "text": ["Record REF1234.", "Record REF123X."],
                "language": "en",
                "score_threshold": 0.6,
            },
        )
        assert response.status_code == 200
        detections = response.get_json()
        assert [
            (item["entity_type"], item["start"], item["end"], item["score"])
            for item in detections[0]
        ] == [("WORKFLOW_REFERENCE", 7, 14, 0.65)]
        assert detections[1] == []

        entry["score_thresholds"] = {"default": 0.6}
        path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
        client = make_app("presidio-analyzer").test_client()
        response = client.post(
            "/analyze",
            json={"text": ["Record REF1234.", "Record REF123X."], "language": "en"},
        )
        assert response.status_code == 200
        detections = response.get_json()
        assert [
            (item["entity_type"], item["start"], item["end"], item["score"])
            for item in detections[0]
        ] == [("WORKFLOW_REFERENCE", 7, 14, 0.65)]
        assert detections[1] == []
        response = client.post(
            "/analyze",
            json={"text": "Record REF1234.", "language": "en", "score_threshold": 0.7},
        )
        assert response.status_code == 200
        assert response.get_json() == []
        anonymizer = make_app("presidio-anonymizer").test_client()
        response = anonymizer.post(
            "/anonymize",
            json={"text": "Record REF1234.", "analyzer_results": detections[0]},
        )
        assert response.status_code == 200
        assert response.get_json()["text"] == "Record <WORKFLOW_REFERENCE>."
    print(
        "PASS: reload YAML, analyze batch over HTTP, override threshold, "
        "anonymize output"
    )


def main() -> None:
    """Run each workflow in an isolated temporary directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gliner", action="store_true", help="Use a real cached GLiNER model"
    )
    parser.add_argument(
        "--huggingface",
        action="store_true",
        help="Use a pinned cached HuggingFace model",
    )
    parser.add_argument(
        "--rest",
        action="store_true",
        help="Use local Analyzer/Anonymizer HTTP apps (requires server dependencies)",
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Validate an exported editor schema (requires dev dependencies)",
    )
    parser.add_argument(
        "--langextract",
        action="store_true",
        help="Check provider config without service calls",
    )
    args = parser.parse_args()
    with TemporaryDirectory(prefix="presidio-config-workflows-") as directory:
        run_default_workflow(Path(directory))
        run_schema_workflow(Path(directory))
        run_identity_workflow(Path(directory))
        run_factory_workflow(Path(directory))
        run_pattern_workflow(Path(directory))
        run_validation_workflow(Path(directory))
        if args.schema:
            run_schema_export_workflow(Path(directory))
        if args.rest:
            run_rest_workflow(Path(directory))
        if args.gliner:
            run_gliner_workflow(Path(directory))
        if args.huggingface:
            run_huggingface_workflow(Path(directory))
        if args.langextract:
            run_langextract_workflow(Path(directory))


if __name__ == "__main__":
    main()
