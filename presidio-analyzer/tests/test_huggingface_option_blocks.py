"""Direct and YAML coverage for HuggingFace library-option blocks."""

from copy import deepcopy
from unittest.mock import MagicMock

import pytest
import yaml

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import HuggingFaceNerRecognizer
from presidio_analyzer.predefined_recognizers.ner import huggingface_ner_recognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


@pytest.fixture
def hf_library(monkeypatch):
    factory = MagicMock()
    factory.return_value.side_effect = lambda text, **kwargs: (
        [{"entity_group": "PER", "start": 8, "end": 20, "score": 0.91}]
        if text == "Patient Alex Example."
        else []
    )
    monkeypatch.setattr(huggingface_ner_recognizer, "hf_pipeline", factory)
    monkeypatch.setattr(huggingface_ner_recognizer, "torch", MagicMock())
    return factory


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_hf_routes_loading_and_prediction_options_and_detects(
    hf_library, tmp_path, source
):
    options = {
        "model_name": "example/model",
        "device": "cpu",
        "model_kwargs": {"revision": "pinned-revision", "trust_remote_code": False},
        "predict_kwargs": {"ignore_labels": ["O"], "batch_size": 1},
    }
    original = deepcopy(options)
    if source == "python":
        recognizer = HuggingFaceNerRecognizer(**options)
    else:
        path = tmp_path / "recognizers.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "supported_languages": ["en"],
                    "recognizers": [{"name": "HuggingFaceNerRecognizer", **options}],
                }
            ),
            encoding="utf-8",
        )
        registry = RecognizerRegistryProvider(
            conf_file=path
        ).create_recognizer_registry()
        recognizer = registry.recognizers[0]
        analyzer = AnalyzerEngine(
            registry=registry,
            nlp_engine=NoOpNlpEngine(
                models=[{"lang_code": "en", "model_name": "no_op"}]
            ),
        )
        assert [
            (r.entity_type, r.start, r.end, r.score)
            for r in analyzer.analyze("Patient Alex Example.", language="en")
        ] == [("PERSON", 8, 20, 0.91)]
        assert analyzer.analyze("Nothing to identify.", language="en") == []

    hf_library.assert_called_once_with(
        "token-classification",
        model="example/model",
        tokenizer="example/model",
        aggregation_strategy="simple",
        device=-1,
        revision="pinned-revision",
        trust_remote_code=False,
    )
    hf_library.return_value.reset_mock()
    results = recognizer.analyze("Patient Alex Example.", entities=["PERSON"])
    assert [(r.entity_type, r.start, r.end, r.score) for r in results] == [
        ("PERSON", 8, 20, 0.91)
    ]
    hf_library.return_value.assert_called_once_with(
        "Patient Alex Example.", ignore_labels=["O"], batch_size=1
    )
    assert options == original


@pytest.mark.parametrize("source", ["python", "yaml"])
@pytest.mark.parametrize(
    "block,key",
    [
        ("model_kwargs", "device"),
        ("model_kwargs", "model"),
        ("model_kwargs", "tokenizer"),
        ("model_kwargs", "task"),
        ("model_kwargs", "device_map"),
        ("predict_kwargs", "aggregation_strategy"),
        ("predict_kwargs", "inputs"),
    ],
)
def test_hf_rejects_block_overlap_before_loading(hf_library, source, block, key):
    options = {"model_name": "example/model", block: {key: "sentinel"}}
    with pytest.raises(ValueError) as exc:
        if source == "python":
            HuggingFaceNerRecognizer(**options)
        else:
            RecognizerRegistryProvider(
                registry_configuration={
                    "recognizers": [{"name": "HuggingFaceNerRecognizer", **options}]
                }
            )
    message = str(exc.value) + str(exc.value.__cause__)
    assert block in message and key in message
    hf_library.assert_not_called()


@pytest.mark.parametrize("block", ["model_kwargs", "predict_kwargs"])
@pytest.mark.parametrize("invalid", [[], "not a mapping", 1, {1: "value"}])
def test_hf_rejects_invalid_blocks_before_loading(hf_library, block, invalid):
    with pytest.raises(ValueError, match=block):
        HuggingFaceNerRecognizer(model_name="example/model", **{block: invalid})
    hf_library.assert_not_called()


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_hf_legacy_flat_options_warn_and_remain_ignored(hf_library, caplog, source):
    options = {
        "model_name": "example/model",
        "device": "cpu",
        "unsupported_option": "value-must-not-be-logged",
    }
    with pytest.warns(DeprecationWarning, match="unsupported_option"):
        if source == "python":
            HuggingFaceNerRecognizer(**options)
        else:
            RecognizerRegistryProvider(
                registry_configuration={
                    "recognizers": [{"name": "HuggingFaceNerRecognizer", **options}]
                }
            ).create_recognizer_registry()
    assert "unsupported_option" not in hf_library.call_args.kwargs
    assert "value-must-not-be-logged" not in caplog.text


def test_hf_does_not_hide_errors_from_explicit_prediction_options(hf_library):
    recognizer = HuggingFaceNerRecognizer(
        model_name="example/model",
        device="cpu",
        predict_kwargs={"invalid_option": True},
    )
    hf_library.return_value.side_effect = TypeError("Unsupported prediction option")
    with pytest.raises(TypeError, match="Unsupported prediction option"):
        recognizer.analyze("Patient Alex Example.", entities=["PERSON"])


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_hf_supports_pipeline_nested_model_loading_options(hf_library, source):
    options = {
        "model_name": "example/model",
        "device": "cpu",
        "model_kwargs": {"model_kwargs": {"local_files_only": True}},
    }
    if source == "python":
        HuggingFaceNerRecognizer(**options)
    else:
        RecognizerRegistryProvider(
            registry_configuration={
                "recognizers": [{"name": "HuggingFaceNerRecognizer", **options}]
            }
        ).create_recognizer_registry()
    assert hf_library.call_args.kwargs["model_kwargs"] == {"local_files_only": True}


@pytest.mark.parametrize("predict_kwargs", [None, {}])
def test_hf_empty_prediction_options_preserve_legacy_error_behavior(
    hf_library, caplog, predict_kwargs
):
    recognizer = HuggingFaceNerRecognizer(
        model_name="example/model", device="cpu", predict_kwargs=predict_kwargs
    )
    hf_library.return_value.side_effect = TypeError("Pipeline failure")
    assert recognizer.analyze("Patient Alex Example.", entities=["PERSON"]) == []
    assert "NER prediction failed" in caplog.text


def test_hf_pipeline_cannot_mutate_callers_nested_model_options(hf_library):
    options = {"model_kwargs": {"local_files_only": True}}
    original = deepcopy(options)

    def build_pipeline(*args, **kwargs):
        kwargs["model_kwargs"]["dtype"] = "library-normalized-value"
        return MagicMock()

    hf_library.side_effect = build_pipeline
    recognizer = HuggingFaceNerRecognizer(
        model_name="example/model", device="cpu", model_kwargs=options
    )
    assert options == original
    assert recognizer.model_kwargs == original
