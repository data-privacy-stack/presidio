"""Behavioral parity across provider, list, YAML and dictionary construction."""

from copy import deepcopy
from unittest.mock import MagicMock

import pytest
import yaml

from presidio_analyzer import PatternRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerListLoader,
)


class FactoryDefaultRecognizer(PatternRecognizer):
    def __init__(
        self, name=None, supported_language="en", context=None, custom_option="default"
    ):
        self.custom_option = custom_option
        super().__init__(
            name=name,
            supported_language=supported_language,
            supported_entity="FACTORY_REFERENCE",
            context=context,
            deny_list=["REF1234"],
            deny_list_score=0.6,
        )
        self.score_thresholds = {"FACTORY_REFERENCE": 0.7}


def snapshot(recognizers):
    return [
        (
            type(r).__name__,
            r.name,
            r.supported_language,
            r.supported_entities,
            r.context,
            r.score_thresholds,
            r.global_regex_flags,
        )
        for r in recognizers
    ]


@pytest.mark.parametrize(
    "entry",
    [
        {"class_name": "FactoryDefaultRecognizer", "custom_option": False},
        {
            "name": "custom",
            "supported_entity": "FACTORY_REFERENCE",
            "deny_list": ["REF1234"],
            "supported_languages": ["en"],
            "context": ["reference"],
            "score_thresholds": {},
        },
    ],
)
def test_provider_list_and_yaml_build_identical_recognizers(entry, tmp_path):
    configuration = {
        "supported_languages": ["en"],
        "global_regex_flags": 0,
        "recognizers": [entry],
    }
    original = deepcopy(configuration)
    expected = RecognizerRegistryProvider(
        registry_configuration=configuration
    ).create_recognizer_registry()
    path = tmp_path / "recognizers.yaml"
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    registry = RecognizerRegistry()
    registry.add_recognizers_from_yaml(path)
    loaded = RecognizerListLoader.get([entry], ["en"], 0)
    assert (
        snapshot(registry.recognizers)
        == snapshot(loaded)
        == snapshot(expected.recognizers)
    )
    assert configuration == original
    if "custom_option" in entry:
        assert registry.recognizers[0].custom_option is False
        assert registry.recognizers[0].score_thresholds == {"FACTORY_REFERENCE": 0.7}
    else:
        assert registry.recognizers[0].context == ["reference"]


def test_custom_plural_entity_and_dictionary_path_match_provider():
    entry = {
        "name": "custom",
        "supported_entities": ["FACTORY_REFERENCE"],
        "deny_list": ["REF1234"],
        "context": ["reference"],
        "score_thresholds": {"default": 0.4},
    }
    configuration = {"supported_languages": ["en"], "recognizers": [entry]}
    registry = RecognizerRegistry()
    registry.add_pattern_recognizer_from_dict(entry)
    provider = RecognizerRegistryProvider(
        registry_configuration=configuration
    ).create_recognizer_registry()
    assert snapshot(registry.recognizers) == snapshot(provider.recognizers)
    assert [
        (r.start, r.end, r.score)
        for r in registry.recognizers[0].analyze(
            "Record REF1234.", ["FACTORY_REFERENCE"]
        )
    ] == [(7, 14, 1.0)]


def test_spec_creation_does_not_construct_and_preserves_omissions(monkeypatch):
    from presidio_analyzer.recognizer_registry import RecognizerFactory

    load = MagicMock()
    monkeypatch.setattr(FactoryDefaultRecognizer, "load", load)
    specs = RecognizerFactory.create_specs(
        {"recognizers": [{"class_name": "FactoryDefaultRecognizer"}]}
    )
    load.assert_not_called()
    assert len(specs) == 1
    assert "custom_option" not in specs[0].constructor_kwargs
    assert "score_thresholds" not in specs[0].attributes
    recognizer = RecognizerFactory.build(specs[0])
    load.assert_called_once()
    assert recognizer.score_thresholds == {"FACTORY_REFERENCE": 0.7}


def test_forwarding_subclass_can_bind_required_parent_arguments():
    from presidio_analyzer.recognizer_registry import RecognizerFactory

    class BoundArgumentRecognizer(PatternRecognizer):
        def __init__(self, **kwargs):
            super().__init__(supported_entity="BOUND", deny_list=["REF1234"], **kwargs)

    recognizer = RecognizerFactory.build_all(
        RecognizerFactory.create_specs(
            {"recognizers": [{"class_name": "BoundArgumentRecognizer"}]}
        )
    )[0]
    assert recognizer.supported_entities == ["BOUND"]


def test_yaml_validation_is_atomic_before_any_recognizer_is_added(
    tmp_path, monkeypatch
):
    path = tmp_path / "invalid.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "strict": True,
                "recognizers": [
                    {"name": "FactoryDefaultRecognizer"},
                    {"name": "CreditCardRecognizer", "replacement_paris": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    load = MagicMock()
    monkeypatch.setattr(FactoryDefaultRecognizer, "load", load)
    registry = RecognizerRegistry()
    with pytest.raises(ValueError) as exc:
        registry.add_recognizers_from_yaml(path)
    assert "replacement_paris" in str(exc.value) + str(exc.value.__cause__)
    load.assert_not_called()
    assert registry.recognizers == []


def test_yaml_addition_rejects_existing_identity_before_loading(tmp_path, monkeypatch):
    registry = RecognizerRegistry(recognizers=[FactoryDefaultRecognizer()])
    path = tmp_path / "duplicate.yaml"
    path.write_text(
        "recognizers:\n- name: FactoryDefaultRecognizer\n", encoding="utf-8"
    )
    load = MagicMock()
    monkeypatch.setattr(FactoryDefaultRecognizer, "load", load)
    with pytest.raises(ValueError, match="Duplicate recognizer"):
        registry.add_recognizers_from_yaml(path)
    load.assert_not_called()
    assert len(registry.recognizers) == 1


def test_filtered_language_does_not_load_external_model(monkeypatch):
    load = MagicMock()
    monkeypatch.setattr(FactoryDefaultRecognizer, "load", load)
    assert (
        RecognizerListLoader.get(
            [{"name": "FactoryDefaultRecognizer", "supported_language": "es"}],
            ["en"],
            26,
        )
        == []
    )
    load.assert_not_called()


def test_dictionary_addition_uses_the_registry_language_filter():
    registry = RecognizerRegistry(supported_languages=["en"])
    registry.add_pattern_recognizer_from_dict(
        {
            "name": "spanish",
            "supported_language": "es",
            "supported_entity": "FACTORY_REFERENCE",
            "deny_list": ["REF1234"],
        }
    )
    assert registry.recognizers == []


def test_nullable_regex_flags_work_on_all_loading_paths():
    entry = {"name": "custom", "supported_entity": "TEST", "deny_list": ["REF1234"]}
    registry = RecognizerRegistry(global_regex_flags=None)
    registry.add_pattern_recognizer_from_dict(entry)
    loaded = RecognizerListLoader.get([entry], ["en"], None)
    for recognizer in [registry.recognizers[0], loaded[0]]:
        assert recognizer.global_regex_flags == 26
        assert [
            (r.start, r.end, r.score)
            for r in recognizer.analyze("Record REF1234.", ["TEST"])
        ] == [(7, 14, 1.0)]


def test_unnamed_custom_dictionary_and_provider_preserve_default_name():
    entry = {"supported_entity": "TEST", "deny_list": ["REF1234"]}
    registry = RecognizerRegistry()
    registry.add_pattern_recognizer_from_dict(entry)
    provider = RecognizerRegistryProvider(
        registry_configuration={"recognizers": [entry]}
    ).create_recognizer_registry()
    assert snapshot(registry.recognizers) == snapshot(provider.recognizers)
    assert registry.recognizers[0].name == "PatternRecognizer"


def test_empty_additions_are_noops_but_not_valid_complete_registries(tmp_path):
    assert RecognizerListLoader.get([], ["en"], 26) == []
    registry = RecognizerRegistry()
    path = tmp_path / "empty.yaml"
    path.write_text("recognizers: []\n", encoding="utf-8")
    registry.add_recognizers_from_yaml(path)
    assert registry.recognizers == []
    with pytest.raises(ValueError):
        RecognizerRegistryProvider(conf_file=path)


def test_legacy_top_level_addition_metadata_warns_and_strict_rejects(tmp_path, caplog):
    config = {
        "supported_countries": ["us"],
        "recognizers": [{"name": "FactoryDefaultRecognizer"}],
    }
    path = tmp_path / "legacy.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    registry = RecognizerRegistry()
    registry.add_recognizers_from_yaml(path)
    assert len(registry.recognizers) == 1
    assert "Ignoring legacy top-level registry metadata keys" in caplog.text
    assert "supported_countries" in caplog.text
    config["strict"] = True
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        RecognizerRegistry().add_recognizers_from_yaml(path)
    assert "supported_countries" in str(exc.value.__cause__)


@pytest.mark.parametrize("languages", [["en"], [{"language": "en"}]])
def test_global_context_reaches_single_language_and_explains_score(
    languages, spacy_nlp_engine
):
    from presidio_analyzer import AnalyzerEngine

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "reference",
                    "supported_entity": "FACTORY_REFERENCE",
                    "deny_list": ["REF1234"],
                    "deny_list_score": 0.5,
                    "context": ["reference"],
                    "supported_languages": languages,
                }
            ],
        }
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)
    results = analyzer.analyze(
        "reference REF1234.", language="en", return_decision_process=True
    )
    assert [(r.start, r.end, r.score) for r in results] == [(10, 17, 0.85)]
    assert results[0].analysis_explanation.supportive_context_word == "reference"
    assert results[0].analysis_explanation.original_score == 0.5
