"""LangExtract's registry compatibility without an optional SDK or remote service."""

import warnings
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.llm_utils import examples_loader, langextract_helper
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import BasicLangExtractRecognizer
from presidio_analyzer.predefined_recognizers.third_party import (
    basic_langextract_recognizer,
    langextract_recognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


@pytest.fixture
def langextract_library(monkeypatch):
    library = SimpleNamespace(
        data=SimpleNamespace(Extraction=SimpleNamespace, ExampleData=SimpleNamespace),
        extract=MagicMock(),
    )
    library.extract.side_effect = lambda **kwargs: SimpleNamespace(
        extractions=(
            [
                SimpleNamespace(
                    extraction_class="person",
                    extraction_text="Alex Example",
                    char_interval=SimpleNamespace(start_pos=8, end_pos=20),
                    alignment_status="MATCH_EXACT",
                    attributes={},
                )
            ]
            if kwargs["text_or_documents"] == "Patient Alex Example."
            else []
        )
    )
    monkeypatch.setattr(langextract_helper, "lx", library)
    monkeypatch.setattr(examples_loader, "lx", library)
    monkeypatch.setattr(langextract_recognizer, "lx", library)
    monkeypatch.setattr(
        basic_langextract_recognizer,
        "lx_factory",
        SimpleNamespace(ModelConfig=SimpleNamespace),
    )
    monkeypatch.delenv("LANGEXTRACT_API_KEY", raising=False)
    return library


@pytest.fixture
def langextract_config_path(tmp_path):
    configuration = yaml.safe_load(
        BasicLangExtractRecognizer.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    )
    configuration["lm_recognizer"]["supported_entities"] = ["PERSON"]
    configuration["langextract"]["model"]["provider"]["extract_params"][
        "max_workers"
    ] = 1
    configuration["langextract"]["model"]["provider"]["language_model_params"][
        "timeout"
    ] = 12
    path = tmp_path / "model.yaml"
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    return path


@pytest.mark.parametrize("source", ["python", "yaml"])
def test_langextract_ignored_options_warn_without_changing_detection(
    tmp_path, langextract_library, langextract_config_path, caplog, source
):
    options = {
        "config_path": str(langextract_config_path),
        "unsupported_option": "value-must-not-be-logged",
    }
    with pytest.warns(DeprecationWarning, match="unsupported_option"):
        if source == "python":
            recognizer = BasicLangExtractRecognizer(**options)
            registry = RecognizerRegistry(recognizers=[recognizer])
        else:
            path = tmp_path / "registry.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "supported_languages": ["en"],
                        "recognizers": [
                            {"name": "BasicLangExtractRecognizer", **options}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            registry = RecognizerRegistryProvider(
                conf_file=path
            ).create_recognizer_registry()

    assert "value-must-not-be-logged" not in caplog.text
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
    )
    results = analyzer.analyze("Patient Alex Example.", language="en")
    assert [(r.entity_type, r.start, r.end, r.score) for r in results] == [
        ("PERSON", 8, 20, 0.95)
    ]
    call = langextract_library.extract.call_args.kwargs
    assert call["max_workers"] == 1
    assert call["config"].provider_kwargs["timeout"] == 12
    assert "unsupported_option" not in call
    assert "unsupported_option" not in call["config"].provider_kwargs
    assert analyzer.analyze("Nothing to identify.", language="en") == []


def test_langextract_named_options_do_not_emit_deprecation_warnings(
    langextract_library, langextract_config_path
):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        BasicLangExtractRecognizer(config_path=str(langextract_config_path))
    assert not [
        item for item in caught if issubclass(item.category, DeprecationWarning)
    ]


def test_langextract_ignored_context_warns_without_changing_context(
    langextract_library, langextract_config_path, caplog
):
    recognizer = BasicLangExtractRecognizer(
        config_path=str(langextract_config_path), context=["context-value-not-logged"]
    )
    assert recognizer.context == []
    assert "context" in caplog.text
    assert "context-value-not-logged" not in caplog.text


@pytest.mark.parametrize("context", [None, []])
def test_langextract_empty_context_does_not_warn(
    langextract_library, langextract_config_path, caplog, context
):
    BasicLangExtractRecognizer(
        config_path=str(langextract_config_path), context=context
    )
    assert "'context'" not in caplog.text


def test_langextract_registry_entity_metadata_is_not_a_deprecated_library_option(
    langextract_library, langextract_config_path, caplog
):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        RecognizerRegistryProvider(
            registry_configuration={
                "recognizers": [
                    {
                        "name": "BasicLangExtractRecognizer",
                        "config_path": str(langextract_config_path),
                        "supported_entities": ["PERSON"],
                    }
                ]
            }
        ).create_recognizer_registry()
    assert not [
        item for item in caught if issubclass(item.category, DeprecationWarning)
    ]
    assert "does not apply 'supported_entity' or 'supported_entities'" in caplog.text
