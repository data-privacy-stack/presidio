# ruff: noqa: D103,D200,D205,E501,F841,I001

import copy
import functools
import re
from pathlib import Path

import pytest
import yaml
from presidio_analyzer import Pattern, PatternRecognizer
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    UsSsnRecognizer,
)
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerConfigurationLoader,
    RecognizerListLoader,
)


def create_mock_pattern_recognizer(lang, entity, name):
    return PatternRecognizer(
        supported_entity=entity,
        supported_language=lang,
        name=name,
        patterns=[Pattern("pat", regex="REGEX", score=1.0)],
    )


class NoKwargsPlural:
    """Mock class that accepts only supported_entities (plural)."""

    def __init__(self, supported_entities=None):
        pass


class NoKwargsSingular:
    """Mock class that accepts only supported_entity (singular)."""

    def __init__(self, supported_entity=None):
        pass


class VarKwargsOnly:
    """Mock class that accepts only **kwargs."""

    def __init__(self, **kwargs):
        pass


class NoKwargsNone:
    """Mock class that accepts neither supported_entity nor supported_entities."""

    def __init__(self):
        pass


class Uninspectable:
    """Mock class where signature inspection fails."""

    __init__ = 123


class StrictParent:
    """Parent class that accepts only supported_entities (no **kwargs)."""

    def __init__(self, supported_entities=None):
        pass


class ChildForwardsKwargs(StrictParent):
    """Child class that accepts **kwargs and forwards to parent."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# Helper: partial to avoid passing empty lang_conf every time
prepare = functools.partial(
    RecognizerListLoader._prepare_recognizer_kwargs, language_conf={}
)


def load_recognizers(recognizers, languages=("en",)):
    return list(RecognizerListLoader.get(recognizers, languages, 26))


def test_predefined_score_thresholds_attach_without_mutating_config():
    config = [
        {
            "name": "CreditCardRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": {"default": 0.4, "CREDIT_CARD": 0.7},
        }
    ]
    original = copy.deepcopy(config)

    recognizers = load_recognizers(config)

    assert recognizers[0].score_thresholds == {
        "default": 0.4,
        "CREDIT_CARD": 0.7,
    }
    assert config == original


def test_custom_multilanguage_score_thresholds_attach_to_each_instance():
    config = [
        {
            "name": "custom_thresholds",
            "type": "custom",
            "supported_entity": "CUSTOM",
            "supported_languages": [{"language": "en"}, {"language": "es"}],
            "patterns": [{"name": "custom", "regex": "x", "score": 0.5}],
            "score_thresholds": {"default": 0.4, "CUSTOM": 0.6},
        }
    ]
    original = copy.deepcopy(config)

    recognizers = load_recognizers(config, ("en", "es"))

    assert {recognizer.supported_language for recognizer in recognizers} == {"en", "es"}
    assert all(
        recognizer.score_thresholds == {"default": 0.4, "CUSTOM": 0.6}
        for recognizer in recognizers
    )
    assert config == original


@pytest.mark.parametrize("score_thresholds", [None, {}])
def test_loader_missing_or_empty_score_thresholds_default_to_empty(score_thresholds):
    config = {
        "name": "CreditCardRecognizer",
        "type": "predefined",
        "supported_language": "en",
    }
    if score_thresholds is not None:
        config["score_thresholds"] = score_thresholds

    recognizer = load_recognizers([config])[0]

    assert recognizer.score_thresholds == {}


def test_loader_explicit_none_score_thresholds_defaults_to_empty():
    recognizer = load_recognizers(
        [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined",
                "supported_language": "en",
                "score_thresholds": None,
            }
        ]
    )[0]

    assert recognizer.score_thresholds == {}


@pytest.mark.parametrize("score_thresholds", [False, 0, "", []])
def test_loader_rejects_falsey_non_mapping_score_thresholds(score_thresholds):
    config = [
        {
            "name": "CreditCardRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": score_thresholds,
        }
    ]

    with pytest.raises(ValueError, match="must be a mapping"):
        load_recognizers(config)


def test_same_name_and_language_entries_keep_distinct_thresholds_and_ids():
    config = [
        {
            "name": "CreditCardRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": {"default": threshold},
        }
        for threshold in (0.4, 0.8)
    ]

    recognizers = load_recognizers(config)

    assert [recognizer.score_thresholds for recognizer in recognizers] == [
        {"default": 0.4},
        {"default": 0.8},
    ]
    assert recognizers[0].name == recognizers[1].name
    assert recognizers[0].supported_language == recognizers[1].supported_language
    assert recognizers[0].id != recognizers[1].id


def test_cleanup_none_removes_entity_keys():
    """Test that explicit None values for entity keys are removed."""
    kwargs = prepare(
        recognizer_conf={"supported_entity": None, "supported_entities": None},
        recognizer_cls=NoKwargsNone,
    )
    assert "supported_entity" not in kwargs
    assert "supported_entities" not in kwargs


def test_plural_only_signature_keeps_plural_and_drops_singular():
    """Test that plural kept, singular dropped for plural-only class."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=NoKwargsPlural,
    )
    assert kwargs["supported_entities"] == ["ENT"]
    assert "supported_entity" not in kwargs


def test_singular_only_signature_converts_plural_to_singular():
    """Test that plural key is converted to singular for singular-only class."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"]}, recognizer_cls=NoKwargsSingular
    )
    assert kwargs["supported_entity"] == "ENT"
    assert "supported_entities" not in kwargs


def test_singular_only_signature_keeps_singular_if_provided():
    """Test that singular key is preserved if provided for singular-only class."""
    kwargs = prepare(
        recognizer_conf={"supported_entity": "ENT_S"}, recognizer_cls=NoKwargsSingular
    )
    assert kwargs["supported_entity"] == "ENT_S"
    assert "supported_entities" not in kwargs


def test_no_kwargs_signature_removes_both():
    """Test that both entity keys are removed if class accepts neither."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=NoKwargsNone,
    )
    assert "supported_entities" not in kwargs
    assert "supported_entity" not in kwargs


def test_var_kwargs_preserves_plural_but_drops_singular_for_safety():
    """Test that plural is kept (compat) but singular is dropped (safety)."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=VarKwargsOnly,
    )
    assert kwargs["supported_entities"] == ["ENT"]
    assert "supported_entity" not in kwargs


def test_uninspectable_signature_drops_entity_keys():
    """Test that entity keys are dropped if signature inspection fails."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=Uninspectable,
    )
    assert "supported_entities" not in kwargs
    assert "supported_entity" not in kwargs


def test_inheritance_forwarding_does_not_crash():
    """Test that inheritance forwarding to strict parent does not crash."""
    # Verify both:
    # 1. dangerous 'supported_entity' (singular) is removed to prevent crash.
    # 2. valid 'supported_entities' (plural) is preserved for compatibility.
    input_kwargs = {"supported_entity": "BAD", "supported_entities": ["ENT"]}
    kwargs = prepare(recognizer_conf=input_kwargs, recognizer_cls=ChildForwardsKwargs)

    # This ensures it doesn't crash when instantiated
    ChildForwardsKwargs(**kwargs)

    assert "supported_entity" not in kwargs
    assert kwargs["supported_entities"] == ["ENT"]


def test_configuration_loader_bad_yaml_raises_value_error(tmp_path):
    """Test that invalid YAML content raises a ValueError."""
    # Create a dummy file with invalid YAML
    f = tmp_path / "bad.yaml"
    f.write_text("invalid: [unclosed_list_without_bracket", encoding="utf-8")

    # Check for the filename part and the error prefix.
    match_pattern = rf"Failed to parse file.*{re.escape(f.name)}"
    with pytest.raises(ValueError, match=match_pattern):
        RecognizerConfigurationLoader.get(conf_file=str(f))


def test_convert_supported_entities_to_entity_uses_first_item():
    """Test that supported_entities list is converted to single supported_entity."""
    conf = {"supported_entities": ["ENT1", "ENT2"]}
    RecognizerListLoader._convert_supported_entities_to_entity(conf)

    assert "supported_entities" not in conf
    assert conf["supported_entity"] == "ENT1"


# ---------------------------------------------------------------------------
# Country filtering and YAML country_code loader utilities
# ---------------------------------------------------------------------------


def test_country_filter_includes_tagged_custom_recognizer():
    """A custom recognizer that opts in via class-level ``COUNTRY_CODE`` is
    included when the filter is loaded with the matching country.
    """
    class _BrCpfRecognizer(PatternRecognizer):
        COUNTRY_CODE = "br"

        def __init__(self):
            super().__init__(
                supported_entity="BR_CPF",
                name="BR CPF Recognizer",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    class _XUsRecognizer(PatternRecognizer):
        COUNTRY_CODE = "us"

        def __init__(self):
            super().__init__(
                supported_entity="X_US_THING",
                name="X US Recognizer",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    br_recognizer = _BrCpfRecognizer()
    us_recognizer = _XUsRecognizer()
    agnostic = create_mock_pattern_recognizer("en", "AGNOSTIC", "Agnostic")

    filtered = RecognizerListLoader.filter_by_countries(
        [br_recognizer, us_recognizer, agnostic], ["br"]
    )

    assert br_recognizer in filtered
    assert us_recognizer not in filtered
    # Locale-agnostic recognizers always survive the filter.
    assert agnostic in filtered


def test_country_filter_warns_on_unknown_country(caplog):
    """When a requested country has no matching recognizer in the input
    list, a WARNING is logged so silent zero-result filters are easier to
    debug.
    """
    class _XUsRecognizer(PatternRecognizer):
        COUNTRY_CODE = "us"

        def __init__(self):
            super().__init__(
                supported_entity="X_US_THING",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    us_recognizer = _XUsRecognizer()

    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        RecognizerListLoader.filter_by_countries([us_recognizer], ["br"])

    warning_messages = [
        r.getMessage() for r in caplog.records if r.levelname == "WARNING"
    ]
    assert any("'br'" in m and "country_code" in m for m in warning_messages), (
        f"expected a country-filter WARNING mentioning 'br' and country_code, "
        f"got {warning_messages!r}"
    )


def test_supported_countries_via_loader_kwarg():
    """``RecognizerListLoader.get(supported_countries=...)`` applies the
    country filter inline alongside the language filter, mirroring how
    ``supported_languages`` is threaded through. This is what allows the
    same filter to be driven from a top-level YAML field with no extra
    plumbing in ``RecognizerRegistry``.
    """
    configuration = RecognizerConfigurationLoader.get(
        registry_configuration={"global_regex_flags": 0}
    )
    recognizers = list(
        RecognizerListLoader.get(**configuration, supported_countries=["us"])
    )
    names = {type(rec).__name__ for rec in recognizers}

    assert "UsSsnRecognizer" in names
    assert "UkNinoRecognizer" not in names
    # Locale-agnostic recognizers survive the filter.
    assert "CreditCardRecognizer" in names


def test_custom_yaml_country_code_flows_through_to_filter(tmp_path):
    """A YAML ``type: custom`` entry with ``country_code:`` is filtered by country.

    End-to-end check: the YAML field flows through
    ``RecognizerListLoader._create_custom_recognizers`` → ``from_dict``
    → ``PatternRecognizer.__init__`` → ``EntityRecognizer.__init__``,
    landing on the instance via ``self._country_code``. The country
    filter then keeps or drops the instance based on the requested set.
    """
    yaml_doc = {
        "supported_languages": ["en"],
        "global_regex_flags": 26,
        "recognizers": [
            {
                "name": "AmNationalIdRecognizer",
                "type": "custom",
                "supported_entity": "AM_NATIONAL_ID",
                "supported_languages": [{"language": "en"}],
                "country_code": "am",
                "patterns": [
                    {"name": "AM 10-digit", "regex": r"\b\d{10}\b", "score": 0.5}
                ],
            }
        ],
    }
    conf_path = tmp_path / "custom_recognizers.yaml"
    conf_path.write_text(yaml.safe_dump(yaml_doc))

    configuration = RecognizerConfigurationLoader.get(conf_file=str(conf_path))
    instances = list(
        RecognizerListLoader.get(**configuration, supported_countries=["am"])
    )

    am = [r for r in instances if getattr(r, "name", None) == "AmNationalIdRecognizer"]
    assert len(am) == 1, (
        "expected the custom AM recognizer to survive the country filter, got "
        f"{[type(r).__name__ for r in instances]}"
    )
    assert am[0].country_code() == "am"

    # The same registry, filtered to a different country, drops it.
    instances_uk = list(
        RecognizerListLoader.get(**configuration, supported_countries=["uk"])
    )
    assert not [
        r for r in instances_uk if getattr(r, "name", None) == "AmNationalIdRecognizer"
    ]


def test_filter_by_countries_rejects_bare_string():
    """A bare ``str`` raises ``TypeError`` rather than silently matching nothing.

    ``countries="us"`` is the most common footgun: it would otherwise
    iterate over characters and match nothing.
    """
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(TypeError, match="iterable of strings"):
        RecognizerListLoader.filter_by_countries([rec], "us")


def test_filter_by_countries_rejects_non_iterable():
    """Non-iterable scalars raise ``TypeError`` early.

    e.g. ``filter_by_countries([rec], 7)`` rather than failing later
    with an opaque error.
    """
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(TypeError, match="iterable of strings"):
        RecognizerListLoader.filter_by_countries([rec], 7)


def test_filter_by_countries_rejects_non_string_element():
    """Each element must be a string; ``[1, 2]`` raises ``TypeError``."""
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(TypeError, match="must be a string"):
        RecognizerListLoader.filter_by_countries([rec], ["us", 2])


def test_filter_by_countries_rejects_blank_element():
    """Empty / whitespace-only codes raise ``ValueError``."""
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(ValueError, match="non-empty"):
        RecognizerListLoader.filter_by_countries([rec], ["us", " "])


def test_filter_by_countries_normalizes_case_and_whitespace():
    """Whitespace is stripped and codes are lower-cased.

    ``" US "`` matches a ``COUNTRY_CODE = "us"`` recognizer.
    """
    class TaggedRecognizer(PatternRecognizer):
        COUNTRY_CODE = "us"

        def __init__(self):
            super().__init__(
                supported_entity="FOO",
                supported_language="en",
                name="TaggedRecognizer",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    tagged = TaggedRecognizer()
    agnostic = create_mock_pattern_recognizer("en", "BAR", "agnostic")

    filtered = RecognizerListLoader.filter_by_countries([tagged, agnostic], ["  US  "])
    names = {type(rec).__name__ for rec in filtered}
    assert "TaggedRecognizer" in names
    # Untagged recognizers are always kept regardless of the filter.
    assert any(getattr(rec, "name", None) == "agnostic" for rec in filtered)


def test_default_recognizers_yaml_country_code_matches_class():
    """Every YAML ``country_code`` matches the class ``COUNTRY_CODE``.

    Sanity check on the shipped ``default_recognizers.yaml``: protects
    against the YAML and the code drifting silently — the loader will
    refuse to load on mismatch.
    """
    conf_path = (
        Path(__file__).resolve().parent.parent
        / "presidio_analyzer"
        / "conf"
        / "default_recognizers.yaml"
    )
    data = yaml.safe_load(conf_path.read_text())
    declared = [
        r
        for r in data.get("recognizers", [])
        if isinstance(r, dict) and "country_code" in r
    ]
    assert declared, "expected at least one country_code: entry in YAML"

    for entry in declared:
        name = entry["name"]
        cls = RecognizerListLoader.get_existing_recognizer_cls(recognizer_name=name)
        # Should not raise — declared YAML matches class.
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf=entry,
            recognizer_cls=cls,
            recognizer_name=name,
        )


def test_yaml_country_code_mismatch_raises():
    """YAML/class disagreement on ``country_code`` raises ``ValueError``.

    The error names both values so the misconfiguration is fixable from
    the error message alone.
    """
    with pytest.raises(ValueError, match="disagrees with class-level"):
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf={"name": "UsSsnRecognizer", "country_code": "uk"},
            recognizer_cls=UsSsnRecognizer,
            recognizer_name="UsSsnRecognizer",
        )


def test_yaml_country_code_on_locale_agnostic_class_raises():
    """YAML ``country_code`` on a class without ``COUNTRY_CODE`` raises.

    The filter has no class-level fact to anchor on. The error message
    points at the fix (set ``COUNTRY_CODE`` on the class, or remove the
    YAML field).
    """
    with pytest.raises(ValueError, match="no ``COUNTRY_CODE`` attribute"):
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf={"name": "CreditCardRecognizer", "country_code": "us"},
            recognizer_cls=CreditCardRecognizer,
            recognizer_name="CreditCardRecognizer",
        )


def test_yaml_country_code_blank_value_raises():
    """A blank / non-string YAML ``country_code`` is rejected up-front."""
    with pytest.raises(ValueError, match="non-empty string"):
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf={"name": "UsSsnRecognizer", "country_code": "   "},
            recognizer_cls=UsSsnRecognizer,
            recognizer_name="UsSsnRecognizer",
        )
