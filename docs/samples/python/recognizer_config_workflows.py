"""Exercise configuration workflows with synthetic data and no model download.

Run from ``presidio-analyzer``:
``uv run python ../docs/samples/python/recognizer_config_workflows.py``

The script writes, loads, edits, and reloads real YAML files in a temporary
directory. Assertions describe the observable result of each user action.
"""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from presidio_analyzer import AnalyzerEngine, PatternRecognizer
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


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


def main() -> None:
    """Run each workflow in an isolated temporary directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gliner", action="store_true", help="Use a real cached GLiNER model"
    )
    args = parser.parse_args()
    with TemporaryDirectory(prefix="presidio-config-workflows-") as directory:
        run_default_workflow(Path(directory))
        if args.gliner:
            run_gliner_workflow(Path(directory))


if __name__ == "__main__":
    main()
