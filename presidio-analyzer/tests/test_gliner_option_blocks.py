"""GLiNER library-option routing through Python and real registry YAML."""

from copy import deepcopy
from unittest.mock import MagicMock

import pytest
import yaml

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import GLiNERRecognizer
from presidio_analyzer.predefined_recognizers.ner import gliner_recognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


@pytest.fixture
def gliner_library(monkeypatch):
    library = MagicMock()
    model = library.from_pretrained.return_value
    model.predict_entities.side_effect = lambda **kwargs: (
        [{"label": "person", "start": 8, "end": 20, "score": 0.88}]
        if kwargs["text"] == "Patient Alex Example."
        else []
    )
    monkeypatch.setattr(gliner_recognizer, "GLiNER", library)
    return library


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_gliner_routes_blocks_and_detects_after_configuration(
    gliner_library, tmp_path, source
):
    options = {
        "model_name": "example/model",
        "map_location": "cpu",
        "entity_mapping": {"person": "PERSON"},
        "model_kwargs": {"local_files_only": True},
        "predict_kwargs": {"return_class_probs": True},
    }
    original = deepcopy(options)
    if source == "python":
        recognizer = GLiNERRecognizer(**options)
    else:
        path = tmp_path / "recognizers.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "supported_languages": ["en"],
                    "recognizers": [{"name": "GLiNERRecognizer", **options}],
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
        ] == [("PERSON", 8, 20, 0.88)]
        assert analyzer.analyze("Nothing to identify.", language="en") == []

    gliner_library.from_pretrained.assert_called_once_with(
        "example/model",
        map_location="cpu",
        load_onnx_model=False,
        onnx_model_file="model.onnx",
        local_files_only=True,
    )
    gliner_library.from_pretrained.return_value.predict_entities.reset_mock()
    results = recognizer.analyze("Patient Alex Example.", entities=["PERSON"])
    assert [(r.entity_type, r.start, r.end, r.score) for r in results] == [
        ("PERSON", 8, 20, 0.88)
    ]
    gliner_library.from_pretrained.return_value.predict_entities.assert_called_once_with(
        text="Patient Alex Example.",
        labels=["person"],
        flat_ner=True,
        threshold=0.3,
        multi_label=False,
        return_class_probs=True,
    )
    assert options == original


@pytest.mark.parametrize("source", ["python", "yaml"])
@pytest.mark.parametrize(
    "block,key",
    [
        ("model_kwargs", "threshold"),
        ("predict_kwargs", "threshold"),
        ("model_kwargs", "model_id"),
        ("predict_kwargs", "text"),
        ("predict_kwargs", "labels"),
    ],
)
def test_gliner_rejects_block_overlap_before_loading(
    gliner_library, source, block, key
):
    options = {"model_name": "example/model", block: {key: "sentinel"}}
    with pytest.raises(ValueError) as exc:
        if source == "python":
            GLiNERRecognizer(**options)
        else:
            RecognizerRegistryProvider(
                registry_configuration={
                    "recognizers": [{"name": "GLiNERRecognizer", **options}]
                }
            )
    message = str(exc.value) + str(exc.value.__cause__)
    assert block in message and key in message
    gliner_library.from_pretrained.assert_not_called()


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_gliner_flat_library_kwargs_warn_and_still_reach_library(
    gliner_library, source
):
    options = {
        "model_name": "example/model",
        "map_location": "cpu",
        "local_files_only": True,
    }
    with pytest.warns(DeprecationWarning, match="model_kwargs"):
        if source == "python":
            GLiNERRecognizer(**options)
        else:
            RecognizerRegistryProvider(
                registry_configuration={
                    "recognizers": [{"name": "GLiNERRecognizer", **options}]
                }
            ).create_recognizer_registry()
    assert gliner_library.from_pretrained.call_args.kwargs["local_files_only"] is True


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_gliner_rejects_duplicate_flat_and_block_options(gliner_library, source):
    options = {
        "model_name": "example/model",
        "local_files_only": True,
        "model_kwargs": {"local_files_only": True},
    }
    with pytest.raises(ValueError) as exc:
        if source == "python":
            GLiNERRecognizer(**options)
        else:
            RecognizerRegistryProvider(
                registry_configuration={
                    "recognizers": [{"name": "GLiNERRecognizer", **options}]
                }
            )
    assert "local_files_only" in str(exc.value) + str(exc.value.__cause__)
    gliner_library.from_pretrained.assert_not_called()


@pytest.mark.parametrize("block", ["model_kwargs", "predict_kwargs"])
@pytest.mark.parametrize("invalid", [[], "not a mapping", 1, {1: "value"}])
def test_gliner_rejects_invalid_option_blocks_before_loading(
    gliner_library, block, invalid
):
    with pytest.raises(ValueError, match=block):
        GLiNERRecognizer(model_name="example/model", **{block: invalid})
    gliner_library.from_pretrained.assert_not_called()


@pytest.mark.parametrize("key", ["map_location", "threshold"])
def test_gliner_subclass_cannot_shadow_parent_options_in_a_block(gliner_library, key):
    class StrictGLiNER(GLiNERRecognizer):
        def __init__(self, model_kwargs=None):
            super().__init__(
                entity_mapping={"person": "PERSON"}, model_kwargs=model_kwargs
            )

    with pytest.raises(ValueError, match=key):
        StrictGLiNER(model_kwargs={key: "sentinel"})
    gliner_library.from_pretrained.assert_not_called()


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_gliner_rejects_reserved_flat_library_arguments(gliner_library, source):
    with pytest.raises(ValueError) as exc:
        if source == "python":
            GLiNERRecognizer(model_id="example/model")
        else:
            RecognizerRegistryProvider(
                registry_configuration={
                    "recognizers": [
                        {"name": "GLiNERRecognizer", "model_id": "example/model"}
                    ]
                }
            )
    assert "model_id" in str(exc.value) + str(exc.value.__cause__)
    gliner_library.from_pretrained.assert_not_called()
